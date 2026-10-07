"""Integration tests for crash recovery and checkpoint resumption."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.migrations.runner import MigrationRunner
from app.database.models import RunModel, SourceRecordModel, BusinessModel
from app.database.repositories.run_repository import RunRepository
from app.database.repositories.source_record_repository import SourceRecordRepository
from app.database.repositories.business_repository import BusinessRepository
from app.core.services.run_service import RunService
from app.workers.run_worker import RunWorker, TaskManager
from app.core.domain.models import RawGoogleRecord

@pytest.fixture
def recovery_env(tmp_path):
    db_file = tmp_path / "recovery.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    MigrationRunner.run_pending(engine)
    TestingSession = sessionmaker(bind=engine)

    from contextlib import contextmanager

    @contextmanager
    def _get_ctx():
        session = TestingSession()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    with patch("app.workers.run_worker.get_db_context", side_effect=_get_ctx), \
         patch("app.database.session.get_db_context", side_effect=_get_ctx):
        yield TestingSession

@pytest.mark.asyncio
async def test_run_crash_recovery_and_checkpoint_continuation(recovery_env):
    """
    Sections 6: Tests complete lifecycle recovery:
    1. Start run
    2. Persist several records
    3. Simulate interruption (crash)
    4. Mark run interrupted (recover_stale_runs)
    5. Resume
    6. Verify existing records remain
    7. Verify no duplicate Google Place IDs
    8. Verify final count
    9. Verify final status
    """
    Session = recovery_env

    # 1. Create run
    with Session() as s:
        svc = RunService(s)
        run = svc.create_run(city="Mumbai", category="Salon", limit=5)
        run_id = run.id

    # Mock scraper to yield initial 3 records, then simulate a crash / interruption
    batch_1 = [
        RawGoogleRecord(
            place_id="ChIJ_REC_1",
            name="Salon Prime 1",
            category="Salon",
            address="Andheri, Mumbai",
            phone="+919876543211",
            profile_url="https://google.com/maps/place/1",
        ),
        RawGoogleRecord(
            place_id="ChIJ_REC_2",
            name="Salon Prime 2",
            category="Salon",
            address="Bandra, Mumbai",
            phone="+919876543212",
            profile_url="https://google.com/maps/place/2",
        ),
        RawGoogleRecord(
            place_id="ChIJ_REC_3",
            name="Salon Prime 3",
            category="Salon",
            address="Juhu, Mumbai",
            phone="+919876543213",
            profile_url="https://google.com/maps/place/3",
        ),
    ]

    async def mock_scrape_batch_1(*args, **kwargs):
        for rec in batch_1:
            yield rec
        # Simulate unexpected crash during scraping
        raise RuntimeError("SIMULATED_PROCESS_CRASH")

    worker = RunWorker()
    with patch("app.workers.run_worker.GoogleMapsScraper.scrape", side_effect=mock_scrape_batch_1):
        try:
            await worker.execute_run(run_id=run_id, city="Mumbai", category="Salon", limit=5)
        except Exception:
            pass

    # 2 & 3. Verify records persisted before the crash
    with Session() as s:
        run_repo = RunRepository(s)
        r = run_repo.get_by_id(run_id)
        assert r.records_saved == 3
        assert r.records_discovered == 3

    # 4. Simulate server restart: recover_stale_runs detects orphaned run and marks it INTERRUPTED
    with Session() as s:
        # Suppose status was left in RUNNING at moment of crash
        run_repo = RunRepository(s)
        run_repo.update_status(run_id, status="RUNNING", force=True)
        stale_count = run_repo.recover_stale_runs()
        assert stale_count == 1
        r_interrupted = run_repo.get_by_id(run_id)
        assert r_interrupted.status == "INTERRUPTED"

    # 5. Resume the run with remaining records (including an overlapping place ID to test dedup)
    batch_2 = [
        # Overlapping Place ID already scraped in batch 1
        RawGoogleRecord(
            place_id="ChIJ_REC_2",
            name="Salon Prime 2",
            category="Salon",
            address="Bandra, Mumbai",
            phone="+919876543212",
            profile_url="https://google.com/maps/place/2",
        ),
        # New record 4
        RawGoogleRecord(
            place_id="ChIJ_REC_4",
            name="Salon Prime 4",
            category="Salon",
            address="Colaba, Mumbai",
            phone="+919876543214",
            profile_url="https://google.com/maps/place/4",
        ),
        # New record 5
        RawGoogleRecord(
            place_id="ChIJ_REC_5",
            name="Salon Prime 5",
            category="Salon",
            address="Powai, Mumbai",
            phone="+919876543215",
            profile_url="https://google.com/maps/place/5",
        ),
    ]

    async def mock_scrape_batch_2(*args, **kwargs):
        seen_initial = kwargs.get("initial_seen_place_ids", set())
        for rec in batch_2:
            # If checkpoint fast-forwarding is used or yielded
            yield rec

    with patch("app.workers.run_worker.GoogleMapsScraper.scrape", side_effect=mock_scrape_batch_2):
        await worker.execute_run(run_id=run_id, city="Mumbai", category="Salon", limit=5)

    # 6, 7, 8, 9. Verify post-resume state
    with Session() as s:
        run_repo = RunRepository(s)
        final_run = run_repo.get_by_id(run_id)

        # 6. Existing records remain
        biz_repo = BusinessRepository(s)
        businesses, total_biz = biz_repo.list_by_run(run_id, page=1, page_size=10)

        # 7. No duplicate Google Place IDs
        place_ids = [b.google_place_id for b in businesses]
        assert len(place_ids) == len(set(place_ids)), "Duplicate place IDs found!"

        # 8. Verify final counts
        assert final_run.records_saved == 5
        assert total_biz == 5
        assert final_run.records_duplicates >= 1  # ChIJ_REC_2 was accounted as duplicate

        # 9. Verify final status
        assert final_run.status == "COMPLETED"
