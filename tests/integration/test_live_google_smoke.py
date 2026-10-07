"""Executable live Google Maps smoke test controlled via RUN_LIVE_GOOGLE_TESTS."""

import os
import pytest
from app.scraping.maps.google_maps_scraper import GoogleMapsScraper
from app.core.services.validation_service import ValidationService

@pytest.mark.asyncio
async def test_live_google_maps_smoke():
    """
    Section 20: Executable live smoke test that runs real Playwright against live Google Maps,
    extracts real places, and validates them into canonical businesses.
    Controlled by RUN_LIVE_GOOGLE_TESTS=1.
    """
    if os.getenv("RUN_LIVE_GOOGLE_TESTS") != "1":
        pytest.skip("Skipping live Google Maps smoke test. Set RUN_LIVE_GOOGLE_TESTS=1 to run.")

    scraper = GoogleMapsScraper()
    validator = ValidationService()

    extracted = []
    async for raw_record in scraper.scrape(city="Mumbai", category="Salon", limit=3, run_id="smoke_live_test_01"):
        extracted.append(raw_record)
        if len(extracted) >= 3:
            break

    assert len(extracted) >= 1, "Scraper yielded 0 records from live Google Maps!"

    # Validate each live record
    valid_businesses = []
    for rec in extracted:
        assert rec.place_id is not None
        assert rec.name is not None
        assert rec.profile_url is not None
        biz, provs, errs = validator.process_raw_record(rec, run_id="live_smoke_run", default_city="Mumbai")
        if biz:
            valid_businesses.append(biz)
            assert biz.name
            assert biz.normalized_name
            assert biz.google_place_id

    assert len(valid_businesses) >= 1, "No valid canonical businesses extracted from live Google Maps!"
