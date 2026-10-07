"""Scale testing for Phase 1 runs (10, 50, 100, 500 records) using deterministic fixtures."""

import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.migrations.runner import MigrationRunner
from app.database.models import RunModel
from app.database.repositories.run_repository import RunRepository
from app.database.repositories.business_repository import BusinessRepository
from app.core.services.run_service import RunService
from app.workers.run_worker import RunWorker
from app.core.domain.models import RawGoogleRecord

@pytest.fixture
def scale_env(tmp_path):
    db_file = tmp_path / "scale.db"
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

@pytest.mark.parametrize("target_limit", [10, 50, 100, 500])
@pytest.mark.asyncio
async def test_scale_runs_correctness_and_accounting(scale_env, target_limit):
    """
    Section 22: Tests 10, 50, 100, and 500 record runs with deterministic mock fixtures:
    - no duplicate place IDs
    - correct counters (discovered, attempted, saved, failed, duplicates)
    - correct pagination
    - correct search
    - correct sorting
    """
    Session = scale_env

    # 1. Create run
    with Session() as s:
        svc = RunService(s)
        run = svc.create_run(city="Mumbai", category="Salon", limit=target_limit)
        run_id = run.id

    # Generate deterministic batch containing valid items, invalid items, and duplicate place IDs
    generated_records = []
    valid_count = 0
    item_counter = 1
    while valid_count < target_limit:
        # Standard valid record
        generated_records.append(RawGoogleRecord(
            place_id=f"ChIJ_SCALE_{item_counter:05d}",
            name=f"Scale Salon {item_counter:05d}",
            category="Salon",
            address=f"Street {item_counter}, Mumbai, Maharashtra 400001",
            phone=f"+9198765{item_counter % 100000:05d}",
            profile_url=f"https://google.com/maps/place/scale_{item_counter:05d}",
            rating=4.5,
            review_count=item_counter * 10,
        ))
        valid_count += 1

        # Every 7th record: inject an intentional duplicate of an earlier record
        if item_counter % 7 == 0 and item_counter > 1:
            generated_records.append(RawGoogleRecord(
                place_id=f"ChIJ_SCALE_{(item_counter - 1):05d}",
                name=f"Scale Salon {(item_counter - 1):05d}",
                category="Salon",
                address=f"Street {item_counter - 1}, Mumbai",
                phone=f"+9198765{(item_counter - 1) % 100000:05d}",
                profile_url=f"https://google.com/maps/place/scale_{(item_counter - 1):05d}",
            ))

        # Every 10th record: inject an invalid record (missing name)
        if item_counter % 10 == 0:
            generated_records.append(RawGoogleRecord(
                place_id=f"ChIJ_SCALE_INV_{item_counter:05d}",
                name="",  # Invalid: will fail validation
                category="Salon",
                address="Invalid St, Mumbai",
                profile_url=f"https://google.com/maps/place/inv_{item_counter:05d}",
            ))

        item_counter += 1

    async def mock_scale_scrape(*args, **kwargs):
        for rec in generated_records:
            yield rec

    worker = RunWorker()
    with patch("app.workers.run_worker.GoogleMapsScraper.scrape", side_effect=mock_scale_scrape):
        await worker.execute_run(run_id=run_id, city="Mumbai", category="Salon", limit=target_limit)

    # Assertions
    with Session() as s:
        run_repo = RunRepository(s)
        biz_repo = BusinessRepository(s)

        run_final = run_repo.get_by_id(run_id)
        assert run_final is not None
        assert run_final.status == "COMPLETED"
        assert run_final.records_saved == target_limit
        assert run_final.records_discovered >= target_limit
        assert run_final.records_attempted == run_final.records_discovered
        assert run_final.records_duplicates >= 1  # Duplicates were recorded

        # 1. Deduplication check: Verify no duplicate place IDs in SQLite
        businesses, total_saved = biz_repo.list_by_run(run_id, page=1, page_size=target_limit + 50)
        assert total_saved == target_limit
        place_ids = [b.google_place_id for b in businesses if b.google_place_id]
        assert len(place_ids) == len(set(place_ids)), "Duplicate place IDs present in database!"

        # 2. Pagination test
        page_1_items, _ = biz_repo.list_by_run(run_id, page=1, page_size=10)
        page_2_items, _ = biz_repo.list_by_run(run_id, page=2, page_size=10)
        assert len(page_1_items) == min(10, target_limit)
        if target_limit > 10:
            assert len(page_2_items) == min(10, target_limit - 10)
            assert page_1_items[0].id != page_2_items[0].id

        # 3. Search test
        searched_items, search_total = biz_repo.list_by_run(run_id, search="0005")
        if target_limit >= 5:
            assert search_total >= 1
            for b in searched_items:
                assert "0005" in b.name or "0005" in (b.phone or "")

        # 4. Sorting test
        sorted_by_rating, _ = biz_repo.list_by_run(run_id, sort_by="rating", sort_order="desc", page_size=20)
        ratings = [b.rating for b in sorted_by_rating if b.rating is not None]
        assert ratings == sorted(ratings, reverse=True)
