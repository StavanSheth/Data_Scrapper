"""Domain data models and value objects."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

@dataclass
class RawGoogleRecord:
    """Raw record as extracted directly from Google Maps."""
    place_id: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    opening_hours: Optional[str] = None
    profile_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: Optional[str] = None
    raw_payload: Dict[str, Any] = field(default_factory=dict)
    scraped_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class NormalizedGoogleRecord:
    """Normalized record following deterministic normalization rules."""
    raw_record: RawGoogleRecord
    name: str
    normalized_name: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    
    # Address breakdown
    address: Optional[str] = None
    street: Optional[str] = None
    locality: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    
    # Geospatial
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Contact
    raw_phone: Optional[str] = None
    normalized_phone: Optional[str] = None
    phone_status: str = "MISSING"
    
    raw_website: Optional[str] = None
    normalized_website: Optional[str] = None
    website_domain: Optional[str] = None
    website_status: str = "MISSING"
    
    email: Optional[str] = None
    email_status: str = "MISSING"
    
    # Metrics
    rating: Optional[float] = None
    review_count: Optional[int] = None
    
    google_place_id: Optional[str] = None
    google_profile_url: Optional[str] = None
    opening_hours: Optional[str] = None
    
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)

@dataclass
class CanonicalBusiness:
    """Canonical business entity for SQLite storage and API delivery."""
    business_id: str
    run_id: str
    source_record_id: Optional[str]
    source: str
    
    name: str
    normalized_name: str
    
    category: Optional[str] = None
    subcategory: Optional[str] = None
    
    address: Optional[str] = None
    street: Optional[str] = None
    locality: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    phone: Optional[str] = None
    normalized_phone: Optional[str] = None
    email: Optional[str] = None
    
    website: Optional[str] = None
    website_domain: Optional[str] = None
    website_status: Optional[str] = None
    
    rating: Optional[float] = None
    review_count: Optional[int] = None
    
    google_place_id: Optional[str] = None
    google_profile_url: Optional[str] = None
    opening_hours: Optional[str] = None
    
    status: str = "VALID"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
