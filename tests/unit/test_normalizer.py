"""Unit tests for NormalizationService."""

import pytest
from app.core.services.normalization_service import NormalizationService

def test_name_normalization_legal_suffixes():
    service = NormalizationService()
    
    assert service.normalize_name("ABC Salon & Spa Pvt. Ltd.") == "abc salon and spa"
    assert service.normalize_name("Enrich Hair & Beauty Salon Private Limited") == "enrich hair and beauty salon"
    assert service.normalize_name("Looks Salon LLP") == "looks salon"
    assert service.normalize_name("Super Cuts Inc.") == "super cuts"
    assert service.normalize_name("  The   Luxury   Spa   Co.  ") == "the luxury spa"

def test_name_normalization_unicode_and_punctuation():
    service = NormalizationService()
    
    # Unicode and special characters
    assert service.normalize_name("L'Oréal Professionnel") == "l oreal professionnel"
    assert service.normalize_name("Café & Bistro @ Mumbai!") == "cafe and bistro mumbai"
    assert service.normalize_name("") == ""
    assert service.normalize_name(None) == ""

def test_phone_normalization_indian_formats():
    service = NormalizationService()
    
    # Standard Indian mobile numbers (+91, 0, no prefix)
    formatted, status = service.normalize_phone("+91 98765 43210")
    assert formatted == "+919876543210"
    assert status == "FOUND"

    formatted, status = service.normalize_phone("09876543210")
    assert formatted == "+919876543210"
    assert status == "FOUND"

    formatted, status = service.normalize_phone("9876543210")
    assert formatted == "+919876543210"
    assert status == "FOUND"

    # With prefix label
    formatted, status = service.normalize_phone("Phone: 091365 67774")
    assert formatted == "+919136567774"
    assert status == "FOUND"

def test_phone_normalization_invalid_and_missing():
    service = NormalizationService()
    
    formatted, status = service.normalize_phone(None)
    assert formatted is None
    assert status == "MISSING"

    formatted, status = service.normalize_phone("")
    assert formatted is None
    assert status == "MISSING"

    formatted, status = service.normalize_phone("12345")
    assert formatted is None
    assert status == "INVALID"

    formatted, status = service.normalize_phone("Call us today!")
    assert formatted is None
    assert status == "INVALID"

def test_url_normalization_and_domain():
    service = NormalizationService()
    
    canonical, domain, status = service.normalize_url("https://www.example.com/about?utm_source=google&id=1")
    assert canonical == "https://www.example.com/about?id=1"
    assert domain == "example.com"
    assert status == "FOUND"

    canonical, domain, status = service.normalize_url("http://sub.domain.co.in/path/")
    assert domain == "sub.domain.co.in"
    assert canonical == "http://sub.domain.co.in/path"
    assert status == "FOUND"

    canonical, domain, status = service.normalize_url("example.com")
    assert domain == "example.com"
    assert canonical == "https://example.com/"
    assert status == "FOUND"

    canonical, domain, status = service.normalize_url(None)
    assert canonical is None
    assert domain is None
    assert status == "MISSING"

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

    # Tolerant with minimal address
    min_parsed = service.parse_address("MG Road, Bengaluru", default_city="Bengaluru")
    assert min_parsed["city"] == "Bengaluru"
    assert min_parsed["street"] == "MG Road"

    # Multi-delimiter address with dash and pipe
    dash_addr = "Plot 12 - New Link Road - Andheri West - Mumbai 400053"
    dash_parsed = service.parse_address(dash_addr)
    assert dash_parsed["city"] == "Mumbai"
    assert dash_parsed["postal_code"] == "400053"
    assert dash_parsed["street"] == "Plot 12, New Link Road"
    assert dash_parsed["locality"] == "Andheri West"

    # Single-line unpunctuated address
    unpunct = "Shop 4 Crystal Plaza New Link Road Andheri West Mumbai 400053"
    unpunct_parsed = service.parse_address(unpunct)
    assert unpunct_parsed["city"] == "Mumbai"
    assert unpunct_parsed["postal_code"] == "400053"
    assert "New Link Road" in unpunct_parsed["street"]
    assert "Andheri West" in unpunct_parsed["locality"]

def test_coordinate_validation():
    service = NormalizationService()
    
    # Valid
    lat, lon = service.validate_coordinates(19.076, 72.877)
    assert lat == 19.076
    assert lon == 72.877

    # String conversion
    lat, lon = service.validate_coordinates("19.12345678", "72.98765432")
    assert lat == 19.1234568
    assert lon == 72.9876543

    # Impossible 0.0, 0.0
    lat, lon = service.validate_coordinates(0.0, 0.0)
    assert lat is None
    assert lon is None

    # Out of range
    lat, lon = service.validate_coordinates(120.0, 72.0)
    assert lat is None
    assert lon is None

    lat, lon = service.validate_coordinates(None, None)
    assert lat is None
    assert lon is None
