"""Pydantic schemas for Run requests and responses."""

from typing import Optional, List
from pydantic import BaseModel, Field

class CreateRunRequest(BaseModel):
    city: str = Field(..., min_length=2, description="City name to search")
    category: str = Field(..., min_length=2, description="Business category")
    limit: int = Field(100, ge=1, le=1000, description="Maximum businesses to scrape")
    confidence_threshold: float = Field(0.80, ge=0.0, le=1.0, description="Match confidence threshold")
    start_immediately: bool = Field(False, description="Whether to start run immediately upon creation (default: False for explicit create/start lifecycle)")

class RunResponse(BaseModel):
    id: str
    city_input: str
    city_normalized: str
    category: Optional[str]
    category_mode: str
    confidence_threshold: float
    requested_limit: int
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    records_discovered: int = 0
    records_saved: int = 0
    records_failed: int = 0
    error_count: int = 0
    error_message: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}

class RunListResponse(BaseModel):
    runs: List[RunResponse]
    total: int
