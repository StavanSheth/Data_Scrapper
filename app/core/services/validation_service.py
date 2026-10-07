"""Validation service for ensuring business records meet canonical standards."""

from typing import Tuple, List, Optional
from datetime import datetime, timezone
import uuid
from app.core.domain.models import RawGoogleRecord, CanonicalBusiness
from app.core.services.normalization_service import NormalizationService
from app.database.models import FieldProvenanceModel

class ValidationService:
    def __init__(self):
        self.normalizer = NormalizationService()

    def process_raw_record(
        self,
        raw: RawGoogleRecord,
        run_id: str,
        source_record_id: Optional[str] = None,
        default_city: Optional[str] = None
    ) -> Tuple[Optional[CanonicalBusiness], List[FieldProvenanceModel], List[str]]:
        """
        Validate and normalize a raw record into a CanonicalBusiness entity.
        Returns: (CanonicalBusiness or None, List of FieldProvenanceModel, errors list).
        """
        errors: List[str] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Validate mandatory field: Business Name
        if not raw.name or not raw.name.strip():
            errors.append("Business name is missing or empty")
            return None, [], errors

        clean_name = raw.name.strip()
        normalized_name = self.normalizer.normalize_name(clean_name)
        if not normalized_name:
            errors.append("Normalized business name is empty")
            return None, [], errors

        # 2. Normalize Phone
        norm_phone, phone_status = self.normalizer.normalize_phone(raw.phone)

        # 3. Normalize Website
        norm_url, website_domain, website_status = self.normalizer.normalize_url(raw.website)

        # 4. Parse Address
        parsed_addr = self.normalizer.parse_address(raw.address, default_city=default_city)

        # 5. Validate Coordinates
        lat, lon = self.normalizer.validate_coordinates(raw.latitude, raw.longitude)

        # 6. Rating & Reviews validation
        clean_rating: Optional[float] = None
        if raw.rating is not None:
            try:
                r = float(raw.rating)
                if 0.0 <= r <= 5.0:
                    clean_rating = round(r, 2)
            except (ValueError, TypeError):
                pass

        clean_reviews: Optional[int] = None
        if raw.review_count is not None:
            try:
                rc = int(raw.review_count)
                if rc >= 0:
                    clean_reviews = rc
            except (ValueError, TypeError):
                pass

        business_id = f"biz_{uuid.uuid4().hex[:12]}"

        business = CanonicalBusiness(
            business_id=business_id,
            run_id=run_id,
            source_record_id=source_record_id,
            source="GOOGLE",
            name=clean_name,
            normalized_name=normalized_name,
            category=raw.category,
            subcategory=None,
            address=raw.address,
            street=parsed_addr.get("street"),
            locality=parsed_addr.get("locality"),
            city=parsed_addr.get("city") or default_city,
            state=parsed_addr.get("state"),
            postal_code=parsed_addr.get("postal_code"),
            country=parsed_addr.get("country") or "India",
            latitude=lat,
            longitude=lon,
            phone=raw.phone,
            normalized_phone=norm_phone,
            email=None,
            website=norm_url or raw.website,
            website_domain=website_domain,
            website_status=website_status,
            rating=clean_rating,
            review_count=clean_reviews,
            google_place_id=raw.place_id,
            google_profile_url=raw.profile_url,
            opening_hours=raw.opening_hours,
            status="VALID",
            created_at=now_iso,
            updated_at=now_iso,
        )

        # Build Field Provenance with realistic, calibrated confidence scores
        provenances: List[FieldProvenanceModel] = []

        def add_prov(field_name: str, val: Optional[str], method: str = "direct_scrape", confidence: float = 0.85):
            if val:
                provenances.append(
                    FieldProvenanceModel(
                        id=f"prov_{uuid.uuid4().hex[:12]}",
                        business_id=business_id,
                        run_id=run_id,
                        field_name=field_name,
                        field_value=str(val),
                        source_type="GOOGLE",
                        source_url=raw.profile_url,
                        source_record_id=source_record_id,
                        extraction_method=method,
                        confidence=round(confidence, 2),
                        extracted_at=now_iso,
                    )
                )

        if raw.place_id:
            add_prov("google_place_id", raw.place_id, method="url_identifier_extraction", confidence=1.0)
        add_prov("name", clean_name, method="title_dom_selector", confidence=0.95)
        add_prov("normalized_name", normalized_name, method="deterministic_normalization", confidence=0.95)
        if raw.category:
            add_prov("category", raw.category, method="category_button_extraction", confidence=0.85)
        if raw.address:
            add_prov("address", raw.address, method="address_dom_extraction", confidence=0.80)
        if parsed_addr.get("street"):
            add_prov("street", parsed_addr["street"], method="address_heuristics_parsing", confidence=0.75)
        if parsed_addr.get("locality"):
            add_prov("locality", parsed_addr["locality"], method="address_heuristics_parsing", confidence=0.75)
        if parsed_addr.get("postal_code"):
            add_prov("postal_code", parsed_addr["postal_code"], method="pin_regex_validation", confidence=0.90)
        if parsed_addr.get("state"):
            add_prov("state", parsed_addr["state"], method="state_dictionary_matching", confidence=0.90)
        if raw.phone:
            add_prov("phone", raw.phone, method="phone_dom_extraction", confidence=0.85)
        if norm_phone:
            phone_conf = 0.95 if phone_status == "FOUND" else 0.75
            add_prov("normalized_phone", norm_phone, method="phone_normalization_e164", confidence=phone_conf)
        if norm_url or raw.website:
            add_prov("website", norm_url or raw.website, method="authority_link_extraction", confidence=0.85)
        if website_domain:
            add_prov("website_domain", website_domain, method="url_domain_canonicalization", confidence=0.90)
        if lat is not None and lon is not None:
            add_prov("coordinates", f"{lat},{lon}", method="coordinate_url_parsing", confidence=0.90)
        if clean_rating is not None:
            add_prov("rating", str(clean_rating), method="rating_metric_extraction", confidence=0.90)
        if clean_reviews is not None:
            add_prov("review_count", str(clean_reviews), method="reviews_metric_extraction", confidence=0.90)

        return business, provenances, errors
