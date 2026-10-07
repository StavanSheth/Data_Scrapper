"""API routes for Scraping Runs management."""

from math import ceil
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.api.dependencies import get_run_service
from app.api.schemas.runs import CreateRunRequest, RunResponse, RunListResponse
from app.api.schemas.businesses import (
    BusinessResponse,
    BusinessDetailResponse,
    PaginatedBusinessResponse,
)
from app.core.services.run_service import RunService

router = APIRouter(prefix="/runs", tags=["Runs"])

import logging

logger = logging.getLogger("runs_api")

@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    request: CreateRunRequest,
    run_service: RunService = Depends(get_run_service),
):
    """
    Create a new scraping run.
    By default, creates a QUEUED run. If start_immediately is true, starts execution.
    """
    try:
        run = run_service.create_run(
            city=request.city,
            category=request.category,
            limit=request.limit,
            confidence_threshold=request.confidence_threshold,
        )
        if request.start_immediately:
            run = run_service.start_run(run.id)
        return run
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create run: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal server error occurred while creating the scraping run.",
        )

@router.get("", response_model=RunListResponse)
def list_runs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    run_service: RunService = Depends(get_run_service),
):
    """List historical scraping runs."""
    runs = run_service.list_runs(limit=limit, offset=offset)
    total = run_service.run_repo.count_runs()
    return RunListResponse(runs=runs, total=total)

@router.get("/{run_id}", response_model=RunResponse)
def get_run(
    run_id: str,
    run_service: RunService = Depends(get_run_service),
):
    """Get status and metrics for a specific run."""
    run = run_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found.")
    return run

@router.post("/{run_id}/start", response_model=RunResponse)
async def start_run(
    run_id: str,
    run_service: RunService = Depends(get_run_service),
):
    """Start or restart a run."""
    try:
        run = run_service.start_run(run_id)
        return run
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start run {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal server error occurred while starting the scraping run.",
        )

@router.post("/{run_id}/resume", response_model=RunResponse)
async def resume_run(
    run_id: str,
    run_service: RunService = Depends(get_run_service),
):
    """Resume an interrupted or stopped scraping run from its persistent checkpoint."""
    try:
        run = run_service.resume_run(run_id)
        return run
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to resume run {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal server error occurred while resuming the scraping run.",
        )

@router.post("/{run_id}/cancel", response_model=RunResponse)
async def cancel_run(
    run_id: str,
    run_service: RunService = Depends(get_run_service),
):
    """Cancel an active run."""
    run = run_service.cancel_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found.")
    return run

@router.get("/{run_id}/businesses", response_model=PaginatedBusinessResponse)
def get_run_businesses(
    run_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, description="Search term across name, address, phone"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    run_service: RunService = Depends(get_run_service),
):
    """Retrieve paginated, searchable businesses discovered in a run."""
    run = run_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found.")

    items, total = run_service.get_businesses(
        run_id=run_id,
        page=page,
        page_size=page_size,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    total_pages = ceil(total / page_size) if total > 0 else 1

    return PaginatedBusinessResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )

@router.get("/{run_id}/businesses/{business_id}", response_model=BusinessDetailResponse)
def get_business_detail(
    run_id: str,
    business_id: str,
    run_service: RunService = Depends(get_run_service),
):
    """Retrieve full details of a business including field-level provenance."""
    business = run_service.get_business_detail(business_id)
    if not business or business.run_id != run_id:
        raise HTTPException(status_code=404, detail="Business not found.")
    return business
