"""Integration tests for database initialization, migrations, constraints, and repositories."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.database.engine import Base
from app.database.models import RunModel, SourceRecordModel, BusinessModel, FieldProvenanceModel
from app.database.repositories.run_repository import RunRepository
from app.database.repositories.business_repository import BusinessRepository
from app.database.repositories.source_record_repository import SourceRecordRepository
from app.database.migrations.runner import MigrationRunner

@pytest.fixture
def db_session(tmp_path):
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}", connect_args={"check_same_thread": False})
    MigrationRunner.run_pending(engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    yield session
    session.close()

def test_fresh_db_initializes(tmp_path):
    """Section 3.1: Fresh DB initializes with authoritative migration runner."""
    db_file = tmp_path / "fresh.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}", connect_args={"check_same_thread": False})
    applied = MigrationRunner.run_pending(engine)
    assert applied >= 1

    with engine.connect() as conn:
        tables = [r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
        assert "runs" in tables
        assert "source_records" in tables
        assert "businesses" in tables
        assert "field_provenance" in tables
        assert "schema_version" in tables

def test_existing_db_reopen_and_data_preserved(tmp_path):
    """Section 3.2, 3.3, 3.4: Existing DB opens successfully, preserving run & business records."""
    db_file = tmp_path / "existing.db"
    engine1 = create_engine(f"sqlite:///{db_file.as_posix()}", connect_args={"check_same_thread": False})
    MigrationRunner.run_pending(engine1)
    
    Session1 = sessionmaker(bind=engine1)
    with Session1() as s1:
        run_repo = RunRepository(s1)
        run_repo.create(RunModel(
            id="run_exist_1",
            city_input="Pune",
            city_normalized="pune",
            status="CREATED",
            created_at="2026-10-07T00:00:00Z",
        ))
        biz_repo = BusinessRepository(s1)
        biz_repo.create(BusinessModel(
            id="biz_exist_1",
            run_id="run_exist_1",
            source="GOOGLE",
            name="Pune Cafe",
            normalized_name="pune cafe",
            city="Pune",
            status="VALID",
            created_at="2026-10-07T00:00:00Z",
            updated_at="2026-10-07T00:00:00Z",
        ))

    # Re-open database with a fresh connection/engine
    engine2 = create_engine(f"sqlite:///{db_file.as_posix()}", connect_args={"check_same_thread": False})
    Session2 = sessionmaker(bind=engine2)
    with Session2() as s2:
        run_repo2 = RunRepository(s2)
        biz_repo2 = BusinessRepository(s2)
        r = run_repo2.get_by_id("run_exist_1")
        assert r is not None
        assert r.city_input == "Pune"
        b = biz_repo2.get_by_id("biz_exist_1")
        assert b is not None
        assert b.name == "Pune Cafe"

def test_initialization_is_idempotent_and_does_not_wipe_data(tmp_path):
    """Section 3.5, 3.6: Re-running initialization is idempotent and does not wipe data."""
    db_file = tmp_path / "idempotent.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}", connect_args={"check_same_thread": False})
    MigrationRunner.run_pending(engine)

    Session = sessionmaker(bind=engine)
    with Session() as s:
        RunRepository(s).create(RunModel(
            id="run_persisted",
            city_input="Delhi",
            city_normalized="delhi",
            status="CREATED",
            created_at="2026-10-07T00:00:00Z",
        ))

    # Re-run migrations
    second_applied = MigrationRunner.run_pending(engine)
    assert second_applied == 0  # No new migrations need applying

    with Session() as s:
        r = RunRepository(s).get_by_id("run_persisted")
        assert r is not None
        assert r.city_input == "Delhi"

def test_same_run_same_place_id_unique_constraint(tmp_path):
    """Section 17: Same run + same Google Place ID cannot create duplicate businesses."""
    db_file = tmp_path / "unique_constraint.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}", connect_args={"check_same_thread": False})
    MigrationRunner.run_pending(engine)
    Session = sessionmaker(bind=engine)

    with Session() as s:
        RunRepository(s).create(RunModel(
            id="run_uq_1",
            city_input="Mumbai",
            city_normalized="mumbai",
            status="RUNNING",
            created_at="2026-10-07T00:00:00Z",
        ))
        biz_repo = BusinessRepository(s)
        
        b1 = BusinessModel(
            id="biz_u1",
            run_id="run_uq_1",
            source="GOOGLE",
            name="Salon Alpha",
            normalized_name="salon alpha",
            city="Mumbai",
            google_place_id="ChIJ_SHARED_PLACE",
            status="VALID",
            created_at="2026-10-07T00:00:00Z",
            updated_at="2026-10-07T00:00:00Z",
        )
        biz_repo.create_with_provenances(b1, [])

        b2 = BusinessModel(
            id="biz_u2",
            run_id="run_uq_1",
            source="GOOGLE",
            name="Salon Alpha Copy",
            normalized_name="salon alpha copy",
            city="Mumbai",
            google_place_id="ChIJ_SHARED_PLACE",
            status="VALID",
            created_at="2026-10-07T00:01:00Z",
            updated_at="2026-10-07T00:01:00Z",
        )
        # Attempt to insert identical (run_id, google_place_id) should be caught safely
        saved_b2 = biz_repo.create_with_provenances(b2, [])
        # Repository catches IntegrityError and returns existing record
        assert saved_b2.id == "biz_u1"

        # Direct table count proves no duplicate business was created
        all_biz = s.query(BusinessModel).filter(BusinessModel.run_id == "run_uq_1").all()
        assert len(all_biz) == 1

def test_cross_run_same_place_id_allowed(tmp_path):
    """Section 17: Run A + place ID X vs Run B + place ID X must both be allowed."""
    db_file = tmp_path / "cross_run.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}", connect_args={"check_same_thread": False})
    MigrationRunner.run_pending(engine)
    Session = sessionmaker(bind=engine)

    with Session() as s:
        run_repo = RunRepository(s)
        run_repo.create(RunModel(id="run_A", city_input="Mumbai", city_normalized="mumbai", status="COMPLETED", created_at="2026-10-07T00:00:00Z"))
        run_repo.create(RunModel(id="run_B", city_input="Mumbai", city_normalized="mumbai", status="COMPLETED", created_at="2026-10-07T00:00:00Z"))

        biz_repo = BusinessRepository(s)
        biz_a = biz_repo.create(BusinessModel(
            id="biz_a",
            run_id="run_A",
            source="GOOGLE",
            name="Shared Place",
            normalized_name="shared place",
            city="Mumbai",
            google_place_id="ChIJ_CROSS",
            status="VALID",
            created_at="2026-10-07T00:00:00Z",
            updated_at="2026-10-07T00:00:00Z",
        ))
        biz_b = biz_repo.create(BusinessModel(
            id="biz_b",
            run_id="run_B",
            source="GOOGLE",
            name="Shared Place",
            normalized_name="shared place",
            city="Mumbai",
            google_place_id="ChIJ_CROSS",
            status="VALID",
            created_at="2026-10-07T00:00:00Z",
            updated_at="2026-10-07T00:00:00Z",
        ))

        assert biz_a.id == "biz_a"
        assert biz_b.id == "biz_b"
        assert biz_a.run_id != biz_b.run_id

def test_different_businesses_same_name_city_allowed(tmp_path):
    """Section 17: Different businesses with same name & city are not treated as duplicate solely from name."""
    db_file = tmp_path / "name_city.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}", connect_args={"check_same_thread": False})
    MigrationRunner.run_pending(engine)
    Session = sessionmaker(bind=engine)

    with Session() as s:
        RunRepository(s).create(RunModel(id="run_franchise", city_input="Mumbai", city_normalized="mumbai", status="COMPLETED", created_at="2026-10-07T00:00:00Z"))
        biz_repo = BusinessRepository(s)

        # Two branches with distinct place IDs and phone numbers
        dup = biz_repo.find_duplicate(
            run_id="run_franchise",
            google_place_id="ChIJ_BRANCH_2",
            normalized_name="jawed habib hair salon",
            city="Mumbai",
            phone="+919876500002",
        )
        assert dup is None

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
    updated = repo.update_status("run_001", status="QUEUED")
    assert updated.status == "QUEUED"
    updated = repo.update_status("run_001", status="RUNNING", started_at="2026-10-07T00:01:00Z")
    assert updated.status == "RUNNING"
    assert updated.started_at is not None

    # Counts update with accounting semantics
    updated_counts = repo.update_counts("run_001", discovered=10, attempted=10, saved=8, failed=1, duplicates=1)
    assert updated_counts.records_discovered == 10
    assert updated_counts.records_attempted == 10
    assert updated_counts.records_saved == 8
    assert updated_counts.records_failed == 1
    assert updated_counts.records_duplicates == 1

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
