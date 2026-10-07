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

    INDIAN_STATES = {
        "andhra pradesh": "Andhra Pradesh",
        "arunachal pradesh": "Arunachal Pradesh",
        "assam": "Assam",
        "bihar": "Bihar",
        "chhattisgarh": "Chhattisgarh",
        "goa": "Goa",
        "gujarat": "Gujarat",
        "haryana": "Haryana",
        "himachal pradesh": "Himachal Pradesh",
        "jharkhand": "Jharkhand",
        "karnataka": "Karnataka",
        "kerala": "Kerala",
        "madhya pradesh": "Madhya Pradesh",
        "maharashtra": "Maharashtra",
        "manipur": "Manipur",
        "meghalaya": "Meghalaya",
        "mizoram": "Mizoram",
        "nagaland": "Nagaland",
        "odisha": "Odisha",
        "punjab": "Punjab",
        "rajasthan": "Rajasthan",
        "sikkim": "Sikkim",
        "tamil nadu": "Tamil Nadu",
        "telangana": "Telangana",
        "tripura": "Tripura",
        "uttar pradesh": "Uttar Pradesh",
        "uttarakhand": "Uttarakhand",
        "west bengal": "West Bengal",
        "delhi": "Delhi",
        "chandigarh": "Chandigarh",
        "puducherry": "Puducherry",
        "jammu and kashmir": "Jammu and Kashmir",
        "ladakh": "Ladakh",
        "mh": "Maharashtra",
        "dl": "Delhi",
        "ka": "Karnataka",
        "tn": "Tamil Nadu",
        "wb": "West Bengal",
        "up": "Uttar Pradesh",
        "gj": "Gujarat",
        "rj": "Rajasthan",
        "ts": "Telangana",
        "ap": "Andhra Pradesh",
    }

    LOCALITY_INDICATORS = (
        "nagar", "colony", "layout", "enclave", "extension", "extn", "sector",
        "block", "phase", "east", "west", "circle", "chowk", "bazaar", "market",
        "complex", "plaza", "heights", "tower", "towers", "bhavan", "wadi", "pada",
        "bandra", "andheri", "juhu", "mulund", "borivali", "kandivali", "malad",
        "goregaon", "powai", "kurla", "ghatkopar", "dadar", "worli", "colaba",
        "chembur", "vashi", "nerul", "kharghar", "thane", "koramangala",
        "indiranagar", "whitefield", "hsr", "btm", "jayanagar", "electronic city",
        "connaught place", "saket", "karol bagh", "lajpat nagar", "rohini", "dwarka"
    )

    @classmethod
    def parse_address(cls, address: Optional[str], default_city: Optional[str] = None) -> Dict[str, Optional[str]]:
        """
        Parse raw Indian address string into structured components:
        street, locality, city, state, postal_code, country.
        Robust to multi-part premises, unformatted landmarks, and missing fields.
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
        raw = re.sub(r"(?i)^(address|addr)[\s:]*", "", raw).strip()

        # 1. Extract 6-digit Indian PIN code
        pin_match = re.search(r"\b([1-9][0-9]{5})\b", raw)
        if pin_match:
            result["postal_code"] = pin_match.group(1)

        # 2. Extract State using comprehensive dictionary
        for state_key, canonical_state in cls.INDIAN_STATES.items():
            if re.search(rf"\b{re.escape(state_key)}\b", raw, re.IGNORECASE):
                result["state"] = canonical_state
                break

        # 3. Detect City
        clean_no_pin = re.sub(r"\b[1-9][0-9]{5}\b", "", raw)
        if default_city and re.search(rf"\b{re.escape(default_city)}\b", clean_no_pin, re.IGNORECASE):
            result["city"] = default_city

        # 4. Split segments and coalesce numerical subparts (e.g., "Shop No. 3", "4", "5")
        raw_parts = [p.strip() for p in raw.split(",") if p.strip()]
        coalesced_parts: list[str] = []
        for p in raw_parts:
            # If current part is just a lone digit or range (e.g. "4", "5", "4 & 5")
            # coalesce with previous segment
            if coalesced_parts and re.match(r"^[\d\s&\-\/]+$", p):
                coalesced_parts[-1] = f"{coalesced_parts[-1]}, {p}"
            else:
                coalesced_parts.append(p)

        # 5. Filter out components that only contain PIN, state, or country
        content_parts: list[str] = []
        for part in coalesced_parts:
            p_clean = part.strip()
            # If part is solely the PIN code
            if re.fullmatch(r"[1-9][0-9]{5}", p_clean):
                continue
            # If part is solely India / Bharat
            if re.fullmatch(r"(?i)(india|bharat)", p_clean):
                continue
            # If part is solely the detected state name
            if result["state"] and re.fullmatch(rf"(?i){re.escape(result['state'])}", p_clean):
                continue
            # If part contains state + PIN (e.g. "Maharashtra 400081")
            if result["state"] and re.search(rf"(?i){re.escape(result['state'])}", p_clean):
                p_sub = re.sub(rf"(?i){re.escape(result['state'])}", "", p_clean)
                p_sub = re.sub(r"\b[1-9][0-9]{5}\b", "", p_sub).strip()
                if not p_sub:
                    continue
                p_clean = p_sub
            # If part is solely the city name
            if result["city"] and re.fullmatch(rf"(?i){re.escape(result['city'])}", p_clean):
                continue
            content_parts.append(p_clean)

        # If city was not determined yet, try taking candidate from penultimate parts
        if not result["city"] and content_parts:
            candidate = content_parts[-1]
            if not any(kw in candidate.lower() for kw in ("road", "marg", "lane", "street", "shop")):
                result["city"] = candidate
                content_parts.pop()

        # 6. Assign Street and Locality intelligently
        if len(content_parts) == 1:
            part = content_parts[0]
            if any(ind in part.lower() for ind in cls.LOCALITY_INDICATORS) and not re.search(r"\b(shop|flat|building|plot|floor|no\.)\b", part, re.IGNORECASE):
                result["locality"] = part
            else:
                result["street"] = part
        elif len(content_parts) == 2:
            result["street"] = content_parts[0]
            result["locality"] = content_parts[1]
        elif len(content_parts) >= 3:
            # Check for locality keywords in the tail
            # e.g., parts: ["Shop No. 3, 4, 5", "Abundance Building", "90 Feet Rd", "Deendayal Nagar", "Mulund East"]
            # Locate split point between street/building descriptors and locality
            split_idx = len(content_parts) - 1
            if len(content_parts) >= 4 and any(ind in content_parts[-2].lower() for ind in cls.LOCALITY_INDICATORS):
                split_idx = len(content_parts) - 2

            result["street"] = ", ".join(content_parts[:split_idx])
            result["locality"] = ", ".join(content_parts[split_idx:])

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
