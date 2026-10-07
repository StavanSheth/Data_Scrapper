"""Unit tests for GoogleMapsParser."""

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

def test_parse_card_lines():
    parser = GoogleMapsParser()
    lines = [
        "Hair Castle Salon",
        "Hair Castle Salon",
        "4.7 (154)",
        "Hairdresser · Gate No. 2, Karma Sankalp Building",
        "Open · Closes 8 pm",
    ]
    data = parser.parse_card_lines(lines, default_category="Salon")
    assert data["name"] == "Hair Castle Salon"
    assert data["rating"] == 4.7
    assert data["review_count"] == 154
    assert data["category"] == "Hairdresser"
    assert "Karma Sankalp Building" in data["address"]
    assert "Closes 8 pm" in data["opening_hours"]

def test_clean_text_field():
    parser = GoogleMapsParser()
    assert parser.clean_text_field("Address", "Address: 123 Main St, Mumbai") == "123 Main St, Mumbai"
    assert parser.clean_text_field("Phone", "Phone: 098765 43210 ") == "098765 43210"
    assert parser.clean_text_field("Phone", None) is None
