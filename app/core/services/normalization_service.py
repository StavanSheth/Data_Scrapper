"""Deterministic normalization service for business entities."""

import re
import unicodedata
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from typing import Optional, Tuple, Dict, Any
import phonenumbers
from app.config.constants import LEGAL_SUFFIXES

class NormalizationService:
    @staticmethod
    def normalize_name(name: Optional[str]) -> str:
        """
        Normalize business name:
        Unicode NFKD -> lowercase -> replace & with and -> strip punctuation ->
        collapse whitespace -> strip legal suffixes.
        """
        if not name or not name.strip():
            return ""

        # Unicode normalization
        text = unicodedata.normalize("NFKD", name)
        text = text.encode("ascii", "ignore").decode("utf-8")
        text = text.lower()

        # Normalize ampersands
        text = re.sub(r"\s*&\s*", " and ", text)

        # Remove punctuation except letters and numbers
        text = re.sub(r"[^\w\s]", " ", text)

        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Remove legal suffixes if at the end of the name
        for suffix in LEGAL_SUFFIXES:
            clean_suffix = re.sub(r"[^\w\s]", "", suffix.lower()).strip()
            pattern = rf"\b{re.escape(clean_suffix)}$"
            text = re.sub(pattern, "", text).strip()

        # Collapse again after suffix removal
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def normalize_phone(phone: Optional[str], default_region: str = "IN") -> Tuple[Optional[str], str]:
        """
        Normalize phone number.
        Returns (normalized_e164_or_national, status).
        Status is FOUND, MISSING, or INVALID.
        """
        if not phone or not phone.strip():
            return None, "MISSING"

        raw = phone.strip()
        # Clean obvious non-phone words
        cleaned = re.sub(r"(?i)^(phone|tel|contact|mobile|call)[\s:]*", "", raw).strip()

        try:
            # Parse using phonenumbers library
            parsed = phonenumbers.parse(cleaned, default_region)
            if phonenumbers.is_valid_number(parsed):
                formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                return formatted, "FOUND"
            elif phonenumbers.is_possible_number(parsed):
                formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                return formatted, "FOUND"
            else:
                return None, "INVALID"
        except phonenumbers.NumberParseException:
            # Fallback regex check for 10-digit Indian numbers
            digits = re.sub(r"\D", "", cleaned)
            if len(digits) == 10 and digits[0] in "6789":
                return f"+91{digits}", "FOUND"
            elif len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
                return f"+{digits}", "FOUND"
            elif len(digits) == 11 and digits.startswith("0") and digits[1] in "6789":
                return f"+91{digits[1:]}", "FOUND"
            return None, "INVALID"

    @staticmethod
    def normalize_url(url: Optional[str]) -> Tuple[Optional[str], Optional[str], str]:
        """
        Normalize URL and extract canonical domain.
        Returns (canonical_url, website_domain, status).
        """
        if not url or not url.strip():
            return None, None, "MISSING"

        raw = url.strip()
        if not re.match(r"^https?://", raw, re.IGNORECASE):
            raw = f"https://{raw}"

        try:
            parsed = urlparse(raw)
            if not parsed.netloc:
                return None, None, "INVALID"

            # Domain normalization: lowercase, strip www.
            netloc = parsed.netloc.lower()
            domain = re.sub(r"^www\.", "", netloc).split(":")[0]

            # Domain must have at least one dot and a valid TLD
            if not re.search(r"\.[a-zA-Z]{2,}$", domain):
                return None, None, "INVALID"

            # Filter tracking query parameters
            query_params = parse_qsl(parsed.query)
            clean_query = [
                (k, v) for k, v in query_params
                if not k.lower().startswith("utm_") and k.lower() not in {"gclid", "fbclid"}
            ]

            # Canonical URL representation
            path = parsed.path.rstrip("/")
            canonical = urlunparse((
                parsed.scheme.lower(),
                netloc,
                path,
                "",
                urlencode(clean_query),
                ""
            ))
            if not canonical.endswith("/") and not path:
                canonical += "/"

            return canonical, domain, "FOUND"
        except Exception:
            return None, None, "INVALID"

    @staticmethod
    def parse_address(address: Optional[str], default_city: Optional[str] = None) -> Dict[str, Optional[str]]:
        """
        Parse raw address string into structured components:
        street, locality, city, state, postal_code, country.
        Tolerant of missing parts.
        """
        result: Dict[str, Optional[str]] = {
            "street": None,
            "locality": None,
            "city": default_city,
            "state": None,
            "postal_code": None,
            "country": "India",
        }

        if not address or not address.strip():
            return result

        raw = address.strip()
        # Clean prefix like "Address: "
        raw = re.sub(r"(?i)^address[\s:]*", "", raw).strip()

        # Extract 6-digit Indian PIN code
        pin_match = re.search(r"\b([1-9][0-9]{5})\b", raw)
        if pin_match:
            result["postal_code"] = pin_match.group(1)

        # Check known Indian states
        states = [
            "Maharashtra", "Delhi", "Karnataka", "Tamil Nadu", "Gujarat",
            "Uttar Pradesh", "Telangana", "West Bengal", "Rajasthan", "Haryana",
            "Kerala", "Punjab", "Madhya Pradesh", "Goa", "Bihar"
        ]
        for state in states:
            if re.search(rf"\b{re.escape(state)}\b", raw, re.IGNORECASE):
                result["state"] = state
                break

        # Split components by comma
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if len(parts) >= 1:
            result["street"] = parts[0]
        if len(parts) >= 2:
            result["locality"] = parts[1]
        if len(parts) >= 3 and not result["city"]:
            # Often city is 3rd or 4th component
            potential_city = re.sub(r"\b[1-9][0-9]{5}\b", "", parts[2]).strip()
            if potential_city:
                result["city"] = potential_city

        return result

    @staticmethod
    def validate_coordinates(lat: Optional[float], lon: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
        """Validate latitude and longitude ranges."""
        if lat is None or lon is None:
            return None, None
        try:
            f_lat = float(lat)
            f_lon = float(lon)
            if -90.0 <= f_lat <= 90.0 and -180.0 <= f_lon <= 180.0:
                if f_lat == 0.0 and f_lon == 0.0:
                    return None, None
                return round(f_lat, 7), round(f_lon, 7)
        except (ValueError, TypeError):
            pass
        return None, None
