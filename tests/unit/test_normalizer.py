"""Unit tests for NormalizationService covering Section 15 test matrix."""

import pytest
from app.core.services.normalization_service import NormalizationService

def test_name_normalization_matrix():
    service = NormalizationService()

    # Section 15 Name Matrix
    assert service.normalize_name("ABC SALON") == "abc salon"
    assert service.normalize_name("ABC Salon - Official") == "abc salon official"
    assert service.normalize_name("  ABC Salon  ") == "abc salon"
    assert service.normalize_name("ABC & Sons") == "abc and sons"
    assert service.normalize_name("ABC's Salon") == "abc s salon"

    # Legal suffixes
    assert service.normalize_name("ABC Salon & Spa Pvt. Ltd.") == "abc salon and spa"
    assert service.normalize_name("Enrich Hair & Beauty Salon Private Limited") == "enrich hair and beauty salon"
    assert service.normalize_name("Looks Salon LLP") == "looks salon"
    assert service.normalize_name("Super Cuts Inc.") == "super cuts"

    # Unicode & empty
    assert service.normalize_name("L'Oréal Professionnel") == "l oreal professionnel"
    assert service.normalize_name("Café & Bistro @ Mumbai!") == "cafe and bistro mumbai"
    assert service.normalize_name("") == ""
    assert service.normalize_name(None) == ""

def test_phone_normalization_matrix():
    service = NormalizationService()

    # Section 15 Phone Matrix
    f, s = service.normalize_phone("+91 9876543210")
    assert f == "+919876543210"
    assert s == "FOUND"

    f, s = service.normalize_phone("09876543210")
    assert f == "+919876543210"
    assert s == "FOUND"

    f, s = service.normalize_phone("98765 43210")
    assert f == "+919876543210"
    assert s == "FOUND"

    f, s = service.normalize_phone("+91-9876543210")
    assert f == "+919876543210"
    assert s == "FOUND"

    f, s = service.normalize_phone("invalid phone")
    assert f is None
    assert s == "INVALID"

    f, s = service.normalize_phone("")
    assert f is None
    assert s == "MISSING"

    f, s = service.normalize_phone(None)
    assert f is None
    assert s == "MISSING"

def test_website_normalization_matrix():
    service = NormalizationService()

    # Section 15 Website Matrix
    c, d, s = service.normalize_url("https://example.com")
    assert c == "https://example.com/"
    assert d == "example.com"
    assert s == "FOUND"

    c, d, s = service.normalize_url("http://example.com/")
    assert c == "http://example.com/"
    assert d == "example.com"
    assert s == "FOUND"

    c, d, s = service.normalize_url("https://www.example.com")
    assert c == "https://www.example.com/"
    assert d == "example.com"
    assert s == "FOUND"

    c, d, s = service.normalize_url("example.com")
    assert c == "https://example.com/"
    assert d == "example.com"
    assert s == "FOUND"

    c, d, s = service.normalize_url("invalid URL")
    assert c is None
    assert d is None
    assert s == "INVALID"

    c, d, s = service.normalize_url("https://www.google.com/maps/place/Salon")
    assert d == "google.com"
    assert s == "FOUND"

    c, d, s = service.normalize_url(None)
    assert c is None
    assert d is None
    assert s == "MISSING"

def test_coordinate_validation_matrix():
    service = NormalizationService()

    # Section 15 Coordinates Matrix
    # Valid India coordinate
    lat, lon = service.validate_coordinates(19.0760, 72.8777)
    assert lat == 19.076
    assert lon == 72.8777

    # 0,0 (impossible location for an Indian business)
    lat, lon = service.validate_coordinates(0, 0)
    assert lat is None
    assert lon is None

    # lat > 90
    lat, lon = service.validate_coordinates(95.0, 72.0)
    assert lat is None
    assert lon is None

    # lon > 180
    lat, lon = service.validate_coordinates(19.0, 195.0)
    assert lat is None
    assert lon is None

    # negative coordinate
    lat, lon = service.validate_coordinates(-19.0, 72.0)
    assert lat == -19.0
    assert lon == 72.0

    # None
    lat, lon = service.validate_coordinates(None, None)
    assert lat is None
    assert lon is None

def test_address_parsing():
    service = NormalizationService()

    raw = "Shop No. 3, 4, 5, Abundance Building, 90 Feet Rd, Deendayal Nagar, Mulund East, Mumbai, Maharashtra 400081"
    parsed = service.parse_address(raw, default_city="Mumbai")

    assert parsed["postal_code"] == "400081"
    assert parsed["state"] == "Maharashtra"
    assert parsed["city"] == "Mumbai"
    assert parsed["street"] == "Shop No. 3, 4, 5, Abundance Building, 90 Feet Rd"
    assert parsed["locality"] == "Deendayal Nagar, Mulund East"
    assert parsed["country"] == "India"
