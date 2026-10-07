"""Parser for extracting structured data from Google Maps DOM elements and URLs."""

import re
from typing import Optional, Tuple, Dict, Any
from urllib.parse import unquote
from app.core.domain.models import RawGoogleRecord

class GoogleMapsParser:
    @staticmethod
    def extract_place_id_and_coords(url: Optional[str]) -> Tuple[Optional[str], Optional[float], Optional[float]]:
        """
        Extract Google Place ID and coordinates from Google Maps URL.
        Example: /maps/place/Salon/data=!4m7!3m6!1s0x...:0x...!8m2!3d19.1701936!4d72.9618542!...19sChIJn6RqQZi55zsRiCAu4cpSQTc
        """
        if not url:
            return None, None, None

        place_id: Optional[str] = None
        lat: Optional[float] = None
        lon: Optional[float] = None

        # Extract Place ID using multi-format cascade
        # 1. Standard protobuf field 19 string (ChIJ...)
        pid_match = re.search(r"19s(ChIJ[\w-]+)", url)
        if pid_match:
            place_id = pid_match.group(1)
        else:
            # 2. Query param place_id=...
            param_match = re.search(r"[?&]place_id=([a-zA-Z0-9_-]+)", url)
            if param_match:
                place_id = param_match.group(1)
            else:
                # 3. Query param ftid=...
                ftid_match = re.search(r"[?&]ftid=([0-9a-zA-Z_:-]+)", url)
                if ftid_match:
                    place_id = ftid_match.group(1)
                else:
                    # 4. Hex CID: 1s0x...:0x...
                    cid_match = re.search(r"1s(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)", url)
                    if cid_match:
                        place_id = cid_match.group(1)
                    elif "/maps/place/" in url:
                        # 5. Deterministic slug extraction if Google changes parameter format
                        slug_match = re.search(r"/maps/place/([^/@?]+)", url)
                        if slug_match:
                            place_id = f"slug_{slug_match.group(1)[:40]}"

        # Extract coordinates: !3d19.1701936!4d72.9618542
        coord_match = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", url)
        if coord_match:
            try:
                lat = float(coord_match.group(1))
                lon = float(coord_match.group(2))
            except (ValueError, TypeError):
                pass
        else:
            # Fallback: @19.1701936,72.9618542
            at_coord_match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
            if at_coord_match:
                try:
                    lat = float(at_coord_match.group(1))
                    lon = float(at_coord_match.group(2))
                except (ValueError, TypeError):
                    pass

        return place_id, lat, lon

    @staticmethod
    def parse_card_lines(lines: list[str], default_category: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse text lines from a Google Maps search card as fallback metadata.
        """
        data: Dict[str, Any] = {
            "name": None,
            "rating": None,
            "review_count": None,
            "category": default_category,
            "address": None,
            "opening_hours": None,
        }

        if not lines:
            return data

        # Line 0 usually contains business name
        data["name"] = lines[0].strip()

        for line in lines[1:]:
            cleaned = line.strip()
            if not cleaned:
                continue

            # Check for rating e.g. "4.7" or "4.7 (120)"
            rating_match = re.match(r"^([1-5]\.\d)(\s*\(([0-9,]+)\))?$", cleaned)
            if rating_match and data["rating"] is None:
                try:
                    data["rating"] = float(rating_match.group(1))
                    if rating_match.group(3):
                        data["review_count"] = int(rating_match.group(3).replace(",", ""))
                except Exception:
                    pass
                continue

            # Check for opening hours first like "Open · Closes 8 pm"
            if re.search(r"(?i)\b(open|closed|closes)\b", cleaned):
                data["opening_hours"] = cleaned
                continue

            # Check for category / address delimiter (e.g. "Hairdresser · Shop No. 3")
            if "·" in cleaned or "•" in cleaned:
                parts = [p.strip() for p in re.split(r"[·•]", cleaned) if p.strip()]
                if len(parts) >= 1:
                    data["category"] = parts[0]
                if len(parts) >= 2 and not data["address"]:
                    data["address"] = parts[-1]
                continue

        return data

    @staticmethod
    def clean_text_field(prefix: str, val: Optional[str]) -> Optional[str]:
        """Strip label prefix from string."""
        if not val:
            return None
        cleaned = re.sub(rf"(?i)^{prefix}[\s:]*", "", val.strip())
        return cleaned.strip() or None
