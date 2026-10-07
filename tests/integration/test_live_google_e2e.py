"""Live end-to-end test against real Google Maps Chromium session."""

import pytest
from app.scraping.maps.google_maps_scraper import GoogleMapsScraper

@pytest.mark.asyncio
async def test_live_google_maps_scraper_real_extraction():
    """
    Executes a real live extraction against Google Maps using Playwright Chromium.
    Proves that the active scraper code successfully navigates live Google Maps,
    locates feed cards, extracts place details, and produces valid records.
    """
    scraper = GoogleMapsScraper(headless=True, request_timeout=30000)
    records = []

    async for record in scraper.scrape(
        city="Mumbai",
        category="Salon",
        limit=3,
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
