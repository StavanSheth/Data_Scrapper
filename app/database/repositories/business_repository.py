"""Repository for Canonical Business entities."""

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc
from sqlalchemy.exc import IntegrityError
from app.database.models import BusinessModel, FieldProvenanceModel

class BusinessRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, business: BusinessModel) -> BusinessModel:
        self.db.add(business)
        self.db.commit()
        self.db.refresh(business)
        return business

    def create_with_provenances(
        self,
        business: BusinessModel,
        provenances: List[FieldProvenanceModel]
    ) -> Optional[BusinessModel]:
        try:
            self.db.add(business)
            self.db.flush()
            for p in provenances:
                p.business_id = business.id
                self.db.add(p)
            self.db.commit()
            self.db.refresh(business)
            return business
        except IntegrityError:
            self.db.rollback()
            if business.google_place_id:
                return self.get_by_google_place_id(business.run_id, business.google_place_id)
            return None

    def get_by_id(self, business_id: str) -> Optional[BusinessModel]:
        return self.db.query(BusinessModel).filter(BusinessModel.id == business_id).first()

    def get_by_google_place_id(self, run_id: str, google_place_id: str) -> Optional[BusinessModel]:
        if not google_place_id:
            return None
        return (
            self.db.query(BusinessModel)
            .filter(
                BusinessModel.run_id == run_id,
                BusinessModel.google_place_id == google_place_id
            )
            .first()
        )

    ALLOWED_SORT_COLUMNS = {
        "created_at": BusinessModel.created_at,
        "name": BusinessModel.name,
        "rating": BusinessModel.rating,
        "review_count": BusinessModel.review_count,
        "city": BusinessModel.city,
        "category": BusinessModel.category,
        "updated_at": BusinessModel.updated_at,
    }

    def find_duplicate(
        self,
        run_id: str,
        google_place_id: Optional[str] = None,
        normalized_name: Optional[str] = None,
        city: Optional[str] = None,
        phone: Optional[str] = None,
        normalized_phone: Optional[str] = None,
        website_domain: Optional[str] = None,
        postal_code: Optional[str] = None,
        address: Optional[str] = None,
    ) -> Optional[BusinessModel]:
        """
        Check for existing duplicate business in run using prioritized signals:
        1. Google Place ID (exact match)
        2. Normalized name + city + phone / normalized_phone
        3. Normalized name + city + website domain (resolves listings lacking phone)
        4. Normalized name + city + postal code (when phone/website missing)
        5. Normalized name + exact address
        """
        # Strong signal 1: Google Place ID
        if google_place_id:
            existing = self.get_by_google_place_id(run_id, google_place_id)
            if existing:
                return existing

        if not normalized_name:
            return None

        # Signal 2: Identical normalized name, city, and phone
        active_phone = phone or normalized_phone
        if city and active_phone:
            existing = (
                self.db.query(BusinessModel)
                .filter(
                    BusinessModel.run_id == run_id,
                    BusinessModel.normalized_name == normalized_name,
                    BusinessModel.city == city,
                    or_(
                        BusinessModel.phone == active_phone,
                        BusinessModel.normalized_phone == active_phone,
                    ),
                )
                .first()
            )
            if existing:
                return existing

        # Signal 3: Normalized name + city + website domain (handles phone-less listings)
        if city and website_domain and website_domain.strip():
            existing = (
                self.db.query(BusinessModel)
                .filter(
                    BusinessModel.run_id == run_id,
                    BusinessModel.normalized_name == normalized_name,
                    BusinessModel.city == city,
                    BusinessModel.website_domain == website_domain.strip(),
                )
                .first()
            )
            if existing:
                return existing

        # Signal 4: Normalized name + city + postal code
        if city and postal_code and postal_code.strip():
            existing = (
                self.db.query(BusinessModel)
                .filter(
                    BusinessModel.run_id == run_id,
                    BusinessModel.normalized_name == normalized_name,
                    BusinessModel.city == city,
                    BusinessModel.postal_code == postal_code.strip(),
                )
                .first()
            )
            if existing:
                return existing

        # Signal 5: Normalized name + exact address
        if address and address.strip():
            existing = (
                self.db.query(BusinessModel)
                .filter(
                    BusinessModel.run_id == run_id,
                    BusinessModel.normalized_name == normalized_name,
                    BusinessModel.address == address.strip(),
                )
                .first()
            )
            if existing:
                return existing

        return None

    def list_by_run(
        self,
        run_id: str,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[BusinessModel], int]:
        """List businesses for run with pagination, search, and sorting."""
        query = self.db.query(BusinessModel).filter(BusinessModel.run_id == run_id)

        if search and search.strip():
            raw_term = search.strip()
            prefix = f"{raw_term}%"
            wildcard = f"%{raw_term}%"
            query = query.filter(
                or_(
                    BusinessModel.normalized_name.like(prefix),
                    BusinessModel.name.ilike(wildcard),
                    BusinessModel.phone.like(prefix),
                    BusinessModel.city.ilike(prefix),
                    BusinessModel.address.ilike(wildcard),
                    BusinessModel.category.ilike(wildcard),
                )
            )

        total = query.count()

        # Safe sorting via strict allowlist
        sort_column = self.ALLOWED_SORT_COLUMNS.get(sort_by, BusinessModel.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        # Pagination
        offset = max(0, (page - 1) * page_size)
        items = query.offset(offset).limit(page_size).all()

        return items, total

    def count_by_run(self, run_id: str) -> int:
        return self.db.query(BusinessModel).filter(BusinessModel.run_id == run_id).count()
