"""Integration tests for FastAPI endpoints covering Section 18 and 19 requirements."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.engine import Base
from app.database.session import get_db
from app.main import app
from app.database.models import RunModel, BusinessModel
from app.database.migrations.runner import MigrationRunner

@pytest.fixture
def client(tmp_path):
    db_file = tmp_path / "test_api.db"
    test_engine = create_engine(
        f"sqlite:///{db_file.as_posix()}",
        connect_args={"check_same_thread": False}
    )
    MigrationRunner.run_pending(test_engine)
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

    run_active = RunModel(
        id="run_active_01",
        city_input="Mumbai",
        city_normalized="mumbai",
        category="Spa",
        status="CREATED",
        records_discovered=0,
        records_saved=0,
        records_failed=0,
        created_at="2026-10-07T00:00:00Z",
    )
    db.add(run_active)

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
        "start_immediately": False,
    }
    res = client.post("/api/runs", json=payload)
    assert res.status_code == 201
    run_data = res.json()
    assert run_data["city_input"] == "Bengaluru"
    assert run_data["category"] == "Spa"
    assert run_data["requested_limit"] == 50
    assert run_data["status"] == "CREATED"
    assert "records_attempted" in run_data
    assert "records_duplicates" in run_data

    # Get by ID
    get_res = client.get(f"/api/runs/{run_data['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == run_data["id"]

def test_create_run_input_validation(client):
    # Reject empty city
    res = client.post("/api/runs", json={"city": "", "category": "Spa", "limit": 10})
    assert res.status_code in [400, 422]

    # Reject empty category
    res = client.post("/api/runs", json={"city": "Mumbai", "category": "", "limit": 10})
    assert res.status_code in [400, 422]

    # Reject limit <= 0
    res = client.post("/api/runs", json={"city": "Mumbai", "category": "Spa", "limit": 0})
    assert res.status_code in [400, 422]

    # Reject limit > 1000
    res = client.post("/api/runs", json={"city": "Mumbai", "category": "Spa", "limit": 1500})
    assert res.status_code in [400, 422]

    # Reject invalid confidence threshold
    res = client.post("/api/runs", json={"city": "Mumbai", "category": "Spa", "limit": 10, "confidence_threshold": 1.5})
    assert res.status_code in [400, 422]

def test_start_and_resume_lifecycle(client):
    with patch("app.workers.run_worker.TaskManager.spawn") as mock_spawn:
        # Start CREATED run -> QUEUED
        start_res = client.post("/api/runs/run_active_01/start")
        assert start_res.status_code == 200
        assert start_res.json()["status"] == "QUEUED"
        assert mock_spawn.called

        # Start COMPLETED run -> rejected with 400
        fail_res = client.post("/api/runs/run_seeded_01/start")
        assert fail_res.status_code == 400

        # Resume COMPLETED run -> rejected with 400
        fail_res2 = client.post("/api/runs/run_seeded_01/resume")
        assert fail_res2.status_code == 400

def test_cancel_run(client):
    # Cancel an active CREATED run -> CANCELLED
    res = client.post("/api/runs/run_active_01/cancel")
    assert res.status_code == 200
    assert res.json()["status"] == "CANCELLED"

    # Cancel a COMPLETED run -> rejected with 400
    fail_res = client.post("/api/runs/run_seeded_01/cancel")
    assert fail_res.status_code == 400

def test_list_runs(client):
    res = client.get("/api/runs")
    assert res.status_code == 200
    data = res.json()
    assert "runs" in data
    assert data["total"] >= 1

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

def test_sort_by_validation(client):
    # Valid sort field
    res_valid = client.get("/api/runs/run_seeded_01/businesses?sort_by=name&sort_order=asc")
    assert res_valid.status_code == 200

    # Invalid sort field (SQL injection or arbitrary string prevention)
    res_invalid = client.get("/api/runs/run_seeded_01/businesses?sort_by=invalid_column;--")
    assert res_invalid.status_code == 422

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
