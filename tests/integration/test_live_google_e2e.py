"""Live end-to-end test against real Google Maps Chromium session and full vertical slice."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.engine import init_db
from app.database.session import get_db_context
from app.database.models import RunModel, SourceRecordModel, BusinessModel, FieldProvenanceModel
from app.database.repositories.run_repository import RunRepository
from app.scraping.maps.google_maps_scraper import GoogleMapsScraper
from app.workers.run_worker import RunWorker

@pytest.mark.asyncio
async def test_live_google_maps_scraper_real_extraction():
    """
    Executes a direct real live extraction against Google Maps using Playwright Chromium.
    Proves that the active scraper code successfully navigates live Google Maps,
    locates feed cards, extracts place details, and produces valid records.
    """
    scraper = GoogleMapsScraper(headless=True, request_timeout=30000)
    records = []

    async for record in scraper.scrape(
        city="Mumbai",
        category="Salon",
        limit=2,
        run_id="test_live_probe",
    ):
        records.append(record)

    # Prove that the live scraper reached Google Maps and yielded real places
    assert len(records) > 0, "Live scraper failed to discover any places from Google Maps"
    
    first = records[0]
    assert first.status == "SUCCESS", f"First live record failed extraction: {first.raw_payload}"
    assert first.name is not None and len(first.name.strip()) > 0, "Live record missing business name"
    assert first.profile_url is not None and "google.com/maps" in first.profile_url
    assert first.place_id is not None
    assert first.place_id.startswith("ChIJ") or first.place_id.startswith("0x") or first.place_id.startswith("slug_")

@pytest.mark.asyncio
async def test_live_google_maps_full_vertical_slice_e2e():
    """
    Executes a full vertical slice integration test with real live Google Maps:
    1. API creates scraping run (HTTP POST /api/runs)
    2. Background worker invokes live Playwright Chromium scraper
    3. Raw extraction is persisted into SQLite source_records
    4. Validation and Normalization produces businesses with field_provenance
    5. Run status and metrics transition to COMPLETED in SQLite
    6. API returns saved businesses with correct pagination and provenance (HTTP GET)
    """
    init_db()
    client = TestClient(app)

    # 1. Create run via API
    create_resp = client.post("/api/runs", json={
        "city": "Mumbai",
        "category": "Salon",
        "limit": 2,
        "start_immediately": False,
    })
    assert create_resp.status_code == 201, f"Failed creating run: {create_resp.text}"
    run_payload = create_resp.json()
    run_id = run_payload["id"]
    assert run_payload["status"] == "CREATED"

    # 2. Worker executes live run against real Google Maps Chromium
    worker = RunWorker()
    await worker.execute_run(
        run_id=run_id,
        city="Mumbai",
        category="Salon",
        limit=2,
    )

    # 3. Verify SQLite Database Persistence
    with get_db_context() as db:
        run_model = RunRepository(db).get_by_id(run_id)
        assert run_model is not None
        assert run_model.status == "COMPLETED", f"Expected COMPLETED but got {run_model.status}: {run_model.error_message}"
        assert run_model.records_discovered >= 1, "Expected at least 1 record discovered"
        assert run_model.records_saved >= 1, "Expected at least 1 business saved"

        # Verify raw source records auditability
        source_records = db.query(SourceRecordModel).filter(SourceRecordModel.run_id == run_id).all()
        assert len(source_records) >= 1
        assert source_records[0].source_type == "GOOGLE"
        assert source_records[0].raw_payload is not None
        assert source_records[0].extraction_status == "SUCCESS"

        # Verify normalized businesses
        businesses = db.query(BusinessModel).filter(BusinessModel.run_id == run_id).all()
        assert len(businesses) >= 1
        first_biz = businesses[0]
        assert first_biz.normalized_name is not None
        assert first_biz.city == "Mumbai"
        assert first_biz.source == "GOOGLE"

        # Verify field provenance metadata
        provenances = db.query(FieldProvenanceModel).filter(FieldProvenanceModel.run_id == run_id).all()
        assert len(provenances) >= 1
        assert any(p.field_name == "name" for p in provenances)
        assert any(p.validator_rule is not None for p in provenances)

    # 4. Verify API Retrieval Integration
    # A. Get Run status via API
    run_resp = client.get(f"/api/runs/{run_id}")
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["status"] == "COMPLETED"
    assert run_data["records_saved"] >= 1
    assert "records_attempted" in run_data
    assert "records_duplicates" in run_data

    # B. List Run businesses via API with pagination
    biz_list_resp = client.get(f"/api/runs/{run_id}/businesses?page=1&page_size=10")
    assert biz_list_resp.status_code == 200
    biz_data = biz_list_resp.json()
    assert biz_data["total"] >= 1
    assert len(biz_data["items"]) >= 1

    # C. Search businesses via API
    first_biz_name = biz_data["items"][0]["name"]
    query_word = first_biz_name.split()[0]
    search_resp = client.get(f"/api/runs/{run_id}/businesses?search={query_word}")
    assert search_resp.status_code == 200
    assert search_resp.json()["total"] >= 1

    # D. Inspect business detail and field provenances via API
    biz_id = biz_data["items"][0]["id"]
    detail_resp = client.get(f"/api/businesses/{biz_id}?run_id={run_id}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["name"] == first_biz_name
    assert len(detail_data["provenances"]) >= 1
