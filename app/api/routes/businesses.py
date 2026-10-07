"""Direct business routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.dependencies import get_run_service
from app.api.schemas.businesses import BusinessDetailResponse
from app.core.services.run_service import RunService

router = APIRouter(prefix="/businesses", tags=["Businesses"])

@router.get("/{business_id}", response_model=BusinessDetailResponse)
def get_business(
    business_id: str,
    run_id: str = Query(..., description="Run ID to enforce execution data boundary"),
    run_service: RunService = Depends(get_run_service),
):
    """Retrieve full details of a business strictly scoped to its parent run."""
    business = run_service.get_business_detail(business_id)
    if not business or business.run_id != run_id:
        raise HTTPException(status_code=404, detail="Business not found within the specified run.")
    return business
