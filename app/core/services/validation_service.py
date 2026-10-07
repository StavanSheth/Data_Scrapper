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

        # Build Field Provenance
        provenances: List[FieldProvenanceModel] = []

        def add_prov(field_name: str, val: Optional[str], method: str = "direct_scrape"):
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
                        confidence=1.0,
                        extracted_at=now_iso,
                    )
                )

        add_prov("name", clean_name)
        add_prov("normalized_name", normalized_name, method="deterministic_normalization")
        add_prov("category", raw.category)
        add_prov("address", raw.address)
        add_prov("phone", raw.phone)
        add_prov("normalized_phone", norm_phone, method="phone_normalization")
        add_prov("website", norm_url or raw.website)
        add_prov("website_domain", website_domain, method="url_domain_extraction")
        if lat is not None and lon is not None:
            add_prov("coordinates", f"{lat},{lon}")

        return business, provenances, errors
