"""Integration tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.engine import Base
from app.database.session import get_db
from app.main import app
from app.database.models import RunModel, BusinessModel

@pytest.fixture
def client(tmp_path):
    db_file = tmp_path / "test_api.db"
    test_engine = create_engine(
        f"sqlite:///{db_file.as_posix()}",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(bind=test_engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    
    # Pre-seed a test run and business
    db = TestingSession()
    run = RunModel(
        id="run_seeded_01",
        city_input="Mumbai",
        city_normalized="mumbai",
        category="Salon",
        status="COMPLETED",
        records_discovered=1,
        records_saved=1,
        records_failed=0,
        created_at="2026-10-07T00:00:00Z",
    )
    db.add(run)
    biz = BusinessModel(
        id="biz_seeded_01",
        run_id="run_seeded_01",
        source="GOOGLE",
        name="Seeded Salon",
        normalized_name="seeded salon",
        city="Mumbai",
        phone="+919876543210",
        normalized_phone="+919876543210",
        status="VALID",
        created_at="2026-10-07T00:00:00Z",
        updated_at="2026-10-07T00:00:00Z",
    )
    db.add(biz)
    db.commit()
    db.close()

    yield test_client
    app.dependency_overrides.clear()

def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"

def test_create_run_and_get(client):
    payload = {
        "city": "Bengaluru",
        "category": "Spa",
        "limit": 50,
        "confidence_threshold": 0.85,
        "start_immediately": False,  # don't start scraper in sync unit test
    }
    res = client.post("/api/runs", json=payload)
    assert res.status_code == 201
    run_data = res.json()
    assert run_data["city_input"] == "Bengaluru"
    assert run_data["category"] == "Spa"
    assert run_data["requested_limit"] == 50
    assert run_data["status"] == "CREATED"

    # Get by ID
    get_res = client.get(f"/api/runs/{run_data['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == run_data["id"]

def test_list_runs(client):
    res = client.get("/api/runs")
    assert res.status_code == 200
    data = res.json()
    assert "runs" in data
    assert data["total"] >= 1

def test_cancel_run(client):
    res = client.post("/api/runs/run_seeded_01/cancel")
    assert res.status_code == 200
    assert res.json()["id"] == "run_seeded_01"

def test_get_businesses_with_search_and_pagination(client):
    res = client.get("/api/runs/run_seeded_01/businesses?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Seeded Salon"

    # Search match
    s_res = client.get("/api/runs/run_seeded_01/businesses?search=seeded")
    assert s_res.status_code == 200
    assert s_res.json()["total"] == 1

    # Search non-match
    no_res = client.get("/api/runs/run_seeded_01/businesses?search=nonexistent")
    assert no_res.status_code == 200
    assert no_res.json()["total"] == 0

def test_get_business_detail(client):
    res = client.get("/api/runs/run_seeded_01/businesses/biz_seeded_01")
    assert res.status_code == 200
    assert res.json()["name"] == "Seeded Salon"

def test_not_found_handling(client):
    res = client.get("/api/runs/nonexistent_id")
    assert res.status_code == 404

    biz_res = client.get("/api/runs/run_seeded_01/businesses/nonexistent_biz")
    assert biz_res.status_code == 404

def test_direct_business_route_run_scoping(client):
    # Missing run_id query param must be rejected (422)
    res_no_run = client.get("/api/businesses/biz_seeded_01")
    assert res_no_run.status_code == 422

    # Wrong run_id must return 404
    res_wrong_run = client.get("/api/businesses/biz_seeded_01?run_id=wrong_run")
    assert res_wrong_run.status_code == 404

    # Correct run_id must succeed
    res_valid = client.get("/api/businesses/biz_seeded_01?run_id=run_seeded_01")
    assert res_valid.status_code == 200
    assert res_valid.json()["id"] == "biz_seeded_01"
