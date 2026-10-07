"""Unit tests for ValidationService covering Section 16 test matrix."""

from app.core.services.validation_service import ValidationService
from app.core.domain.models import RawGoogleRecord

def test_validation_successful_record():
    service = ValidationService()
    raw = RawGoogleRecord(
        place_id="ChIJ1234567890",
        name="Enrich Salon & Academy Pvt Ltd",
        category="Hairdresser",
        address="12 MG Road, Bandra West, Mumbai, Maharashtra 400050",
        phone="+91 98200 12345",
        website="https://www.enrichsalon.com/locations?utm_source=gmb",
        rating=4.6,
        review_count=350,
        latitude=19.055,
        longitude=72.835,
        profile_url="https://maps.google.com/place/123",
    )

    business, provenances, errors = service.process_raw_record(
        raw=raw,
        run_id="run_test_001",
        source_record_id="src_001",
        default_city="Mumbai",
    )

    assert errors == []
    assert business is not None
    assert business.name == "Enrich Salon & Academy Pvt Ltd"
    assert business.normalized_name == "enrich salon and academy"
    assert business.normalized_phone == "+919820012345"
    assert business.website_domain == "enrichsalon.com"
    assert business.postal_code == "400050"
    assert business.city == "Mumbai"
    assert business.rating == 4.6
    assert business.review_count == 350
    assert business.latitude == 19.055
    assert business.longitude == 72.835
    assert len(provenances) >= 7

def test_validation_missing_name_fails():
    service = ValidationService()
    # Missing / empty name
    raw = RawGoogleRecord(
        place_id="ChIJ00000",
        name="",
        phone="+919876543210",
    )
    business, provenances, errors = service.process_raw_record(raw=raw, run_id="run_test_002")
    assert business is None
    assert len(errors) > 0
    assert "Business name is missing" in errors[0]

    # None name
    raw_none = RawGoogleRecord(place_id="ChIJ00001", name=None)
    business_none, _, errors_none = service.process_raw_record(raw=raw_none, run_id="run_test_002")
    assert business_none is None
    assert len(errors_none) > 0

def test_validation_numeric_bounds_ratings_and_reviews():
    service = ValidationService()

    # Rating > 5 -> null
    raw_high_rating = RawGoogleRecord(
        place_id="ChIJ00002",
        name="Overrated Salon",
        rating=5.8,
        review_count=20,
    )
    b, _, _ = service.process_raw_record(raw_high_rating, "run_test_003")
    assert b is not None
    assert b.rating is None
    assert b.review_count == 20

    # Negative rating -> null
    raw_neg_rating = RawGoogleRecord(
        place_id="ChIJ00003",
        name="Negative Rating Salon",
        rating=-1.5,
    )
    b, _, _ = service.process_raw_record(raw_neg_rating, "run_test_003")
    assert b is not None
    assert b.rating is None

    # Negative review count -> null
    raw_neg_reviews = RawGoogleRecord(
        place_id="ChIJ00004",
        name="Negative Review Count Salon",
        rating=4.2,
        review_count=-10,
    )
    b, _, _ = service.process_raw_record(raw_neg_reviews, "run_test_003")
    assert b is not None
    assert b.rating == 4.2
    assert b.review_count is None

def test_validation_malformed_optional_fields_keeps_business():
    service = ValidationService()
    # Bad phone, bad website, out-of-range coordinates
    raw = RawGoogleRecord(
        place_id="ChIJ99999",
        name="Royal Cuts Salon",
        category="Salon",
        address="Near Railway Station, Mumbai",
        phone="INVALID_PHONE_TEXT",
        website="not-a-valid-url-###",
        latitude=999.0,
        longitude=-999.0,
    )

    business, provenances, errors = service.process_raw_record(
        raw=raw,
        run_id="run_test_004",
        default_city="Mumbai",
    )

    # Business is still accepted with sanitized fields
    assert errors == []
    assert business is not None
    assert business.name == "Royal Cuts Salon"
    assert business.normalized_phone is None
    assert business.website_domain is None
    assert business.latitude is None
    assert business.longitude is None
