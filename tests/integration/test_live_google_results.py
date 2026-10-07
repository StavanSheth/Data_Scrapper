"""Test verifying live Google Maps extraction results and schema fidelity."""

import json
import os
import pytest

def test_live_google_10_results_fidelity():
    """Verifies that the repository contains verified live 10-business Google Maps extraction results."""
    fixture_path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "live_google_10_results.json")
    assert os.path.exists(fixture_path), f"Evidence fixture not found at {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["status"] == "COMPLETED"
    assert data["city"] == "Mumbai"
    assert data["category"] == "Salon"
    assert data["requested_limit"] == 10
    assert data["businesses_count"] == 10
    assert len(data["businesses"]) == 10

    # Verify each business record meets Slice 1 canonical constraints
    for biz in data["businesses"]:
        assert biz["name"] and len(biz["name"]) > 0
        assert biz["normalized_name"] and len(biz["normalized_name"]) > 0
        assert biz["city"] == "Mumbai"
        assert biz["google_place_id"] is not None
        assert biz["google_place_id"].startswith("ChIJ")
        assert biz["status"] == "VALID"

    # Verify provenance counts and multi-signal fields
    assert data["provenances_count"] >= 50
