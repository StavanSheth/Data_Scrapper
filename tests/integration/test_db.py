"""Integration tests for database models and repositories."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.engine import Base
from app.database.models import RunModel, SourceRecordModel, BusinessModel, FieldProvenanceModel
from app.database.repositories.run_repository import RunRepository
from app.database.repositories.business_repository import BusinessRepository
from app.database.repositories.source_record_repository import SourceRecordRepository

@pytest.fixture
def db_session(tmp_path):
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    yield session
    session.close()

def test_run_crud_and_status_update(db_session):
    repo = RunRepository(db_session)
    run = RunModel(
        id="run_001",
        city_input="Mumbai",
        city_normalized="mumbai",
        category="Salon",
        requested_limit=100,
        status="CREATED",
        created_at="2026-10-07T00:00:00Z",
    )
    repo.create(run)

    fetched = repo.get_by_id("run_001")
    assert fetched is not None
    assert fetched.city_input == "Mumbai"
    assert fetched.status == "CREATED"

    # Status update
    updated = repo.update_status("run_001", status="RUNNING", started_at="2026-10-07T00:01:00Z")
    assert updated.status == "RUNNING"
    assert updated.started_at is not None

    # Counts update
    updated_counts = repo.update_counts("run_001", discovered=10, saved=8, failed=2)
    assert updated_counts.records_discovered == 10
    assert updated_counts.records_saved == 8
    assert updated_counts.records_failed == 2

def test_business_deduplication(db_session):
    run_repo = RunRepository(db_session)
    biz_repo = BusinessRepository(db_session)

    run = RunModel(
        id="run_dedup_01",
        city_input="Mumbai",
        city_normalized="mumbai",
        status="RUNNING",
        created_at="2026-10-07T00:00:00Z",
    )
    run_repo.create(run)

    biz1 = BusinessModel(
        id="biz_1",
        run_id="run_dedup_01",
        source="GOOGLE",
        name="Luxe Salon",
        normalized_name="luxe salon",
        city="Mumbai",
        phone="+919876543210",
        google_place_id="ChIJ_A1",
        status="VALID",
        created_at="2026-10-07T00:00:00Z",
        updated_at="2026-10-07T00:00:00Z",
    )
    biz_repo.create(biz1)

    # 1. Duplicate by Place ID
    dup1 = biz_repo.find_duplicate(
        run_id="run_dedup_01",
        google_place_id="ChIJ_A1",
    )
    assert dup1 is not None
    assert dup1.id == "biz_1"

    # 2. Duplicate by Name + City + Phone
    dup2 = biz_repo.find_duplicate(
        run_id="run_dedup_01",
        normalized_name="luxe salon",
        city="Mumbai",
        phone="+919876543210",
    )
    assert dup2 is not None
    assert dup2.id == "biz_1"

    # 3. Different business
    not_dup = biz_repo.find_duplicate(
        run_id="run_dedup_01",
        google_place_id="ChIJ_DIFFERENT",
        normalized_name="other salon",
        city="Mumbai",
        phone="+919999999999",
    )
    assert not_dup is None

def test_business_pagination_and_search(db_session):
    run_repo = RunRepository(db_session)
    biz_repo = BusinessRepository(db_session)

    run_repo.create(RunModel(
        id="run_search_01",
        city_input="Mumbai",
        city_normalized="mumbai",
        status="COMPLETED",
        created_at="2026-10-07T00:00:00Z",
    ))

    for i in range(15):
        biz_repo.create(BusinessModel(
            id=f"b_{i}",
            run_id="run_search_01",
            source="GOOGLE",
            name=f"Salon Brand {i}" if i % 2 == 0 else f"Spa Studio {i}",
            normalized_name=f"salon brand {i}" if i % 2 == 0 else f"spa studio {i}",
            city="Mumbai",
            status="VALID",
            created_at=f"2026-10-07T00:{i:02d}:00Z",
            updated_at=f"2026-10-07T00:{i:02d}:00Z",
        ))

    # Test page size
    items, total = biz_repo.list_by_run("run_search_01", page=1, page_size=5)
    assert len(items) == 5
    assert total == 15

    # Test search filter
    items_search, total_search = biz_repo.list_by_run("run_search_01", search="Spa")
    assert total_search == 7
    for item in items_search:
        assert "Spa" in item.name
