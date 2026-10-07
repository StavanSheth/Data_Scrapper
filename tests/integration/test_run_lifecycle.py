"""Integration tests for run lifecycle, partial failure, and persistence."""

import pytest
import asyncio
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.engine import Base
from app.database.models import RunModel, BusinessModel
from app.database.repositories.run_repository import RunRepository
from app.database.repositories.business_repository import BusinessRepository
from app.core.domain.models import RawGoogleRecord
from app.workers.run_worker import RunWorker

from app.database.migrations.runner import MigrationRunner

@pytest.fixture
def db_context(tmp_path):
    db_file = tmp_path / "lifecycle.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}", connect_args={"check_same_thread": False})
    MigrationRunner.run_pending(engine)
    TestingSession = sessionmaker(bind=engine)
    return TestingSession, db_file

@pytest.mark.asyncio
async def test_partial_failure_handling(db_context):
    TestingSession, db_file = db_context

    # Create run
    session = TestingSession()
    run = RunModel(
        id="run_lifecycle_01",
        city_input="Mumbai",
        city_normalized="mumbai",
        category="Salon",
        requested_limit=4,
        status="CREATED",
        created_at="2026-10-07T00:00:00Z",
    )
    session.add(run)
    session.commit()
    session.close()

    # Mock scraper returning 3 valid records and 1 malformed (empty name)
    async def mock_scrape(*args, **kwargs):
        yield RawGoogleRecord(
            place_id="ChIJ1",
            name="Salon Alpha",
            address="1 Alpha St, Mumbai",
            phone="+919876543211",
        )
        yield RawGoogleRecord(
            place_id="ChIJ2",
            name="Salon Beta",
            address="2 Beta St, Mumbai",
            phone="+919876543212",
        )
        # Malformed record (empty name) -> should fail validation
        yield RawGoogleRecord(
            place_id="ChIJ3",
            name="",
            address="3 Malformed St, Mumbai",
        )
        yield RawGoogleRecord(
            place_id="ChIJ4",
            name="Salon Delta",
            address="4 Delta St, Mumbai",
            phone="+919876543214",
        )

    worker = RunWorker()
    worker.scraper.scrape = mock_scrape

    # Override get_db_context in worker to use our test DB
    from contextlib import contextmanager
    @contextmanager
    def test_db_ctx():
        s = TestingSession()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    with patch("app.workers.run_worker.get_db_context", side_effect=test_db_ctx):
        await worker.execute_run(
            run_id="run_lifecycle_01",
            city="Mumbai",
            category="Salon",
            limit=4,
        )

    # Verify run status is PARTIAL
    session = TestingSession()
    run_repo = RunRepository(session)
    biz_repo = BusinessRepository(session)

    final_run = run_repo.get_by_id("run_lifecycle_01")
    assert final_run.status == "PARTIAL"
    assert final_run.records_discovered == 4
    assert final_run.records_saved == 3
    assert final_run.records_failed == 1

    # Verify all 3 successful businesses are stored
    businesses, total = biz_repo.list_by_run("run_lifecycle_01", page=1, page_size=10)
    assert total == 3
    names = [b.name for b in businesses]
    assert "Salon Alpha" in names
    assert "Salon Beta" in names
    assert "Salon Delta" in names
    session.close()

@pytest.mark.asyncio
async def test_persistence_across_reconnect(db_context):
    TestingSession, db_file = db_context

    # Session 1: save a business
    s1 = TestingSession()
    run = RunModel(
        id="run_persist_01",
        city_input="Pune",
        city_normalized="pune",
        status="COMPLETED",
        created_at="2026-10-07T00:00:00Z",
    )
    s1.add(run)
    biz = BusinessModel(
        id="biz_persist_01",
        run_id="run_persist_01",
        source="GOOGLE",
        name="Persistent Salon",
        normalized_name="persistent salon",
        city="Pune",
        status="VALID",
        created_at="2026-10-07T00:00:00Z",
        updated_at="2026-10-07T00:00:00Z",
    )
    s1.add(biz)
    s1.commit()
    s1.close()

    # Reconnect to the database file with a fresh engine and session
    new_engine = create_engine(f"sqlite:///{db_file.as_posix()}", connect_args={"check_same_thread": False})
    NewSession = sessionmaker(bind=new_engine)
    s2 = NewSession()

    r = s2.query(RunModel).filter(RunModel.id == "run_persist_01").first()
    assert r is not None
    assert r.city_input == "Pune"

    b = s2.query(BusinessModel).filter(BusinessModel.id == "biz_persist_01").first()
    assert b is not None
    assert b.name == "Persistent Salon"
    s2.close()
