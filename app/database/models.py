"""SQLAlchemy database models for Slice 1."""

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from app.database.engine import Base

class RunModel(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True, index=True)
    city_input = Column(String, nullable=False)
    city_normalized = Column(String, nullable=False)
    category = Column(String, nullable=True)
    categories = Column(Text, nullable=True)  # JSON list
    category_mode = Column(String, nullable=False, default="selected")
    confidence_threshold = Column(Float, nullable=False, default=0.80)
    requested_limit = Column(Integer, nullable=False, default=100)
    status = Column(String, nullable=False, default="CREATED", index=True)
    
    started_at = Column(String, nullable=True)
    completed_at = Column(String, nullable=True)
    cancelled_at = Column(String, nullable=True)
    
    total_google_records = Column(Integer, default=0)
    total_platform_records = Column(Integer, default=0)
    total_matched = Column(Integer, default=0)
    total_google_unmatched = Column(Integer, default=0)
    total_platform_unmatched = Column(Integer, default=0)
    
    records_discovered = Column(Integer, default=0)
    records_saved = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(String, nullable=False)

    source_records = relationship("SourceRecordModel", back_populates="run", cascade="all, delete-orphan")
    businesses = relationship("BusinessModel", back_populates="run", cascade="all, delete-orphan")


class SourceRecordModel(Base):
    __tablename__ = "source_records"

    id = Column(String, primary_key=True, index=True)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False, index=True)
    platform_id = Column(String, nullable=True)
    source_type = Column(String, nullable=False, default="GOOGLE")
    source_url = Column(Text, nullable=True)
    external_id = Column(String, nullable=True, index=True)  # Google Place ID
    raw_name = Column(Text, nullable=True)
    raw_address = Column(Text, nullable=True)
    raw_phone = Column(String, nullable=True)
    raw_email = Column(String, nullable=True)
    raw_website = Column(Text, nullable=True)
    raw_category = Column(String, nullable=True)
    raw_latitude = Column(Float, nullable=True)
    raw_longitude = Column(Float, nullable=True)
    raw_rating = Column(Float, nullable=True)
    raw_review_count = Column(Integer, nullable=True)
    raw_payload = Column(Text, nullable=True)  # JSON
    extraction_status = Column(String, nullable=False, default="SUCCESS")
    scraped_at = Column(String, nullable=False)

    run = relationship("RunModel", back_populates="source_records")
    businesses = relationship("BusinessModel", back_populates="source_record")


from sqlalchemy import Index

class BusinessModel(Base):
    __tablename__ = "businesses"
    __table_args__ = (
        Index("ix_businesses_run_name", "run_id", "normalized_name"),
        Index("ix_businesses_run_created", "run_id", "created_at"),
        Index("ix_businesses_run_city", "run_id", "city"),
        Index("uq_businesses_run_place_id", "run_id", "google_place_id", unique=True, sqlite_where=Column("google_place_id").is_not(None)),
    )

    id = Column(String, primary_key=True, index=True)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False, index=True)
    source = Column(String, nullable=False, default="GOOGLE")
    source_record_id = Column(String, ForeignKey("source_records.id"), nullable=True, index=True)

    name = Column(String, nullable=False)
    normalized_name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=True)
    subcategory = Column(String, nullable=True)

    address = Column(Text, nullable=True)
    street = Column(String, nullable=True)
    locality = Column(String, nullable=True)
    city = Column(String, nullable=True, index=True)
    state = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    country = Column(String, nullable=True)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    phone = Column(String, nullable=True, index=True)
    normalized_phone = Column(String, nullable=True)
    email = Column(String, nullable=True)

    website = Column(Text, nullable=True)
    website_domain = Column(String, nullable=True, index=True)
    website_status = Column(String, nullable=True)

    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)

    google_place_id = Column(String, nullable=True, index=True)
    google_profile_url = Column(Text, nullable=True)
    opening_hours = Column(Text, nullable=True)

    status = Column(String, nullable=False, default="VALID")
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

    run = relationship("RunModel", back_populates="businesses")
    source_record = relationship("SourceRecordModel", back_populates="businesses")
    provenances = relationship("FieldProvenanceModel", back_populates="business", cascade="all, delete-orphan")


class FieldProvenanceModel(Base):
    __tablename__ = "field_provenance"

    id = Column(String, primary_key=True, index=True)
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False, index=True)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False, index=True)
    field_name = Column(String, nullable=False)
    field_value = Column(Text, nullable=True)
    source_type = Column(String, nullable=False)
    source_url = Column(Text, nullable=True)
    source_record_id = Column(String, nullable=True)
    extraction_method = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    raw_fragment = Column(Text, nullable=True)  # Raw snippet/text from source
    validator_rule = Column(String, nullable=True)  # Validation or normalization rule applied
    extracted_at = Column(String, nullable=False)

    business = relationship("BusinessModel", back_populates="provenances")


# Indexes
Index("idx_runs_status", RunModel.status)
Index("idx_source_records_run_ext", SourceRecordModel.run_id, SourceRecordModel.external_id)
Index("idx_businesses_run_place", BusinessModel.run_id, BusinessModel.google_place_id)
Index("idx_businesses_name_city", BusinessModel.normalized_name, BusinessModel.city)
Index("idx_provenance_biz_field", FieldProvenanceModel.business_id, FieldProvenanceModel.field_name)
