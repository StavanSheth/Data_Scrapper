"""Direct business routes."""

from fastapi import APIRouter, Depends, HTTPException
from app.api.dependencies import get_run_service
from app.api.schemas.businesses import BusinessDetailResponse
from app.core.services.run_service import RunService

router = APIRouter(prefix="/businesses", tags=["Businesses"])

@router.get("/{business_id}", response_model=BusinessDetailResponse)
def get_business(
    business_id: str,
    run_service: RunService = Depends(get_run_service),
):
    """Retrieve full details of a business by ID."""
    business = run_service.get_business_detail(business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")
    return business
