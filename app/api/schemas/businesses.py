"""Pydantic schemas for Business requests and responses."""

from typing import Optional, List
from pydantic import BaseModel

class FieldProvenanceResponse(BaseModel):
    id: str
    field_name: str
    field_value: Optional[str]
    source_type: str
    source_url: Optional[str]
    extraction_method: Optional[str]
    confidence: Optional[float]
    extracted_at: str

    model_config = {"from_attributes": True}

class BusinessResponse(BaseModel):
    id: str
    run_id: str
    source: str
    name: str
    normalized_name: str
    category: Optional[str]
    subcategory: Optional[str] = None
    address: Optional[str]
    street: Optional[str]
    locality: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal_code: Optional[str]
    country: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    phone: Optional[str]
    normalized_phone: Optional[str]
    email: Optional[str]
    website: Optional[str]
    website_domain: Optional[str]
    website_status: Optional[str]
    rating: Optional[float]
    review_count: Optional[int]
    google_place_id: Optional[str]
    google_profile_url: Optional[str]
    opening_hours: Optional[str]
    status: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

class BusinessDetailResponse(BusinessResponse):
    provenances: List[FieldProvenanceResponse] = []

class PaginatedBusinessResponse(BaseModel):
    items: List[BusinessResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
