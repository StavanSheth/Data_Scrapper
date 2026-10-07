"""Unit tests for GoogleMapsParser covering Section 14 test matrix."""

from app.scraping.maps.parser import GoogleMapsParser

def test_extract_place_id_and_coords():
    parser = GoogleMapsParser()
    url = (
        "https://www.google.com/maps/place/The+Alchemic+Beauty+Curl+and+Colour+Salon/"
        "data=!4m7!3m6!1s0x3be7b998416aa49f:0x374152cae12e2088!8m2!3d19.1701936!4d72.9618542"
        "!16s%2Fg%2F11q8rp266k!19sChIJn6RqQZi55zsRiCAu4cpSQTc?authuser=0"
    )
    place_id, lat, lon = parser.extract_place_id_and_coords(url)
    assert place_id == "ChIJn6RqQZi55zsRiCAu4cpSQTc"
    assert lat == 19.1701936
    assert lon == 72.9618542

def test_extract_coords_fallback_format():
    parser = GoogleMapsParser()
    url = "https://www.google.com/maps/place/Salon/@19.0760,72.8777,15z/data=!4m2!3m1!1s0x0:0x123"
    place_id, lat, lon = parser.extract_place_id_and_coords(url)
    assert lat == 19.0760
    assert lon == 72.8777

def test_parse_normal_business():
    parser = GoogleMapsParser()
    lines = [
        "Hair Castle Salon",
        "4.7 (154)",
        "Hairdresser · Gate No. 2, Karma Sankalp Building",
        "098765 43210",
        "Open · Closes 8 pm",
    ]
    data = parser.parse_card_lines(lines, default_category="Salon")
    assert data["name"] == "Hair Castle Salon"
    assert data["rating"] == 4.7
    assert data["review_count"] == 154
    assert data["category"] == "Hairdresser"
    assert "Karma Sankalp Building" in data["address"]
    assert data["phone"] == "098765 43210"

def test_parse_business_no_phone():
    parser = GoogleMapsParser()
    lines = [
        "Quiet Spa Studio",
        "4.5 (80)",
        "Day Spa · Linking Road, Bandra West",
        "Open · Closes 9 pm",
    ]
    data = parser.parse_card_lines(lines, default_category="Spa")
    assert data["name"] == "Quiet Spa Studio"
    assert data["phone"] is None

def test_parse_business_no_website():
    parser = GoogleMapsParser()
    lines = [
        "Corner Barber",
        "4.0 (12)",
        "Barber shop · Dadar Market, Mumbai",
    ]
    data = parser.parse_card_lines(lines, default_category="Barber")
    assert data["name"] == "Corner Barber"
    assert data.get("website") is None

def test_parse_business_indian_mobile_and_landline():
    parser = GoogleMapsParser()
    # Mobile
    lines_mob = [
        "Mumbai Wellness Clinic",
        "Clinic · Andheri East, Mumbai",
        "+91 98765 43210",
    ]
    data_mob = parser.parse_card_lines(lines_mob)
    assert data_mob["phone"] == "+91 98765 43210"

    # Landline
    lines_land = [
        "South Bombay Salon",
        "Beauty salon · Fort, Mumbai",
        "022 2200 1234",
    ]
    data_land = parser.parse_card_lines(lines_land)
    assert data_land["phone"] == "022 2200 1234"

def test_parse_rating_no_reviews_and_no_rating():
    parser = GoogleMapsParser()
    # Rating but no reviews
    lines_nr = [
        "New Cafe",
        "5.0",
        "Cafe · Juhu, Mumbai",
    ]
    data_nr = parser.parse_card_lines(lines_nr)
    assert data_nr["rating"] == 5.0
    assert data_nr["review_count"] is None

    # No rating at all
    lines_none = [
        "Brand New Dental",
        "Dentist · Worli, Mumbai",
        "Opens tomorrow at 10 am",
    ]
    data_none = parser.parse_card_lines(lines_none)
    assert data_none["rating"] is None
    assert data_none["review_count"] is None

def test_parse_addresses_and_pin_codes():
    parser = GoogleMapsParser()
    # Mumbai address with PIN
    lines = [
        "Luxe Parlour",
        "Salon · Shop 4, High Street Mall, Senapati Bapat Marg, Lower Parel, Mumbai, Maharashtra 400013",
    ]
    data = parser.parse_card_lines(lines)
    assert "400013" in data["address"]
    assert "Mumbai" in data["address"]

    # Missing address
    lines_missing = [
        "Mystery Outlet",
        "Store",
    ]
    data_missing = parser.parse_card_lines(lines_missing)
    assert data_missing.get("address") is None

def test_clean_text_field():
    parser = GoogleMapsParser()
    assert parser.clean_text_field("Address", "Address: 123 Main St, Mumbai") == "123 Main St, Mumbai"
    assert parser.clean_text_field("Phone", "Phone: 098765 43210 ") == "098765 43210"
    assert parser.clean_text_field("Phone", None) is None
