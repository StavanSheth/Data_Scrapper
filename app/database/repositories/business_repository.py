"""Repository for Canonical Business entities."""

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc
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
    ) -> BusinessModel:
        self.db.add(business)
        self.db.flush()
        for p in provenances:
            p.business_id = business.id
            self.db.add(p)
        self.db.commit()
        self.db.refresh(business)
        return business

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

    def find_duplicate(
        self,
        run_id: str,
        google_place_id: Optional[str] = None,
        normalized_name: Optional[str] = None,
        city: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Optional[BusinessModel]:
        """Check for existing duplicate business in run."""
        # Strong signal: Google Place ID
        if google_place_id:
            existing = self.get_by_google_place_id(run_id, google_place_id)
            if existing:
                return existing

        # Secondary signal: identical normalized name, city, and phone
        if normalized_name and city and phone:
            existing = (
                self.db.query(BusinessModel)
                .filter(
                    BusinessModel.run_id == run_id,
                    BusinessModel.normalized_name == normalized_name,
                    BusinessModel.city == city,
                    BusinessModel.phone == phone,
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
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    BusinessModel.name.ilike(term),
                    BusinessModel.normalized_name.ilike(term),
                    BusinessModel.address.ilike(term),
                    BusinessModel.city.ilike(term),
                    BusinessModel.phone.ilike(term),
                    BusinessModel.category.ilike(term),
                )
            )

        total = query.count()

        # Sorting
        sort_column = getattr(BusinessModel, sort_by, BusinessModel.created_at)
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
