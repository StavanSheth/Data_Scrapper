"""Application service for managing scraping runs and businesses."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.database.models import RunModel, BusinessModel
from app.database.repositories.run_repository import RunRepository
from app.database.repositories.business_repository import BusinessRepository
from app.workers.run_worker import RunWorker, TaskManager

class RunService:
    def __init__(self, db: Session):
        self.db = db
        self.run_repo = RunRepository(db)
        self.business_repo = BusinessRepository(db)
        self.worker = RunWorker()

    def create_run(
        self,
        city: str,
        category: str,
        limit: int = 100,
        confidence_threshold: float = 0.80,
    ) -> RunModel:
        """Create a new run entity with status CREATED."""
        if not city or not city.strip():
            raise ValueError("City must not be empty.")
        if not category or not category.strip():
            raise ValueError("Category must not be empty.")
        if limit <= 0:
            raise ValueError("Limit must be greater than 0.")
        if limit > 1000:
            raise ValueError("Limit must be less than or equal to 1000.")
        if confidence_threshold < 0.0 or confidence_threshold > 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0.")

        clean_city = city.strip()
        clean_cat = category.strip()
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        run = RunModel(
            id=run_id,
            city_input=clean_city,
            city_normalized=clean_city.lower(),
            category=clean_cat,
            categories=json.dumps([clean_cat]),
            category_mode="selected",
            confidence_threshold=confidence_threshold,
            requested_limit=limit,
            status="CREATED",
            created_at=now_iso,
        )
        return self.run_repo.create(run)

    def start_run(self, run_id: str) -> RunModel:
        """Transitions newly created run to QUEUED and launches background scraping task."""
        run = self.run_repo.get_by_id(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found.")

        if run.status in ["RUNNING", "QUEUED"]:
            return run

        if run.status != "CREATED":
            raise ValueError(
                f"Cannot start run in '{run.status}' state. "
                f"Use POST /api/runs/{run_id}/resume to resume or create a new run."
            )

        # Transition to QUEUED
        self.run_repo.update_status(run_id, status="QUEUED")
        run.status = "QUEUED"

        # Supervised task spawning via TaskManager
        TaskManager.spawn(
            run_id=run.id,
            coro=self.worker.execute_run(
                run_id=run.id,
                city=run.city_input,
                category=run.category or "business",
                limit=run.requested_limit,
            )
        )
        return run

    def resume_run(self, run_id: str) -> RunModel:
        """Resumes an interrupted or stopped scraping run from its persistent SQLite checkpoint."""
        run = self.run_repo.get_by_id(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found.")

        if run.status in ["RUNNING", "QUEUED"]:
            return run

        if run.status not in ["INTERRUPTED", "FAILED", "CANCELLED", "CREATED"]:
            raise ValueError(f"Cannot resume run in '{run.status}' state.")

        # ponytail: Checkpoint reconstruction from SQLite source records across process crashes, upgrade trigger: distributed persistent browser session / remote CDP worker pool.
        self.run_repo.update_status(run_id, status="QUEUED", error_message=None)
        run.status = "QUEUED"
        run.error_message = None

        TaskManager.spawn(
            run_id=run.id,
            coro=self.worker.execute_run(
                run_id=run.id,
                city=run.city_input,
                category=run.category or "business",
                limit=run.requested_limit,
            )
        )
        return run

    def cancel_run(self, run_id: str) -> Optional[RunModel]:
        """Request persistent cancellation of run via SQLite and task cancel."""
        run = self.run_repo.get_by_id(run_id)
        if not run:
            return None
        if run.status in ["COMPLETED", "FAILED", "CANCELLED"]:
            raise ValueError(f"Cannot cancel run in '{run.status}' state.")
        now_iso = datetime.now(timezone.utc).isoformat()
        self.run_repo.update_status(run_id, status="CANCELLED", cancelled_at=now_iso)
        TaskManager.cancel(run_id)
        run.status = "CANCELLED"
        run.cancelled_at = now_iso
        return run

    def get_run(self, run_id: str) -> Optional[RunModel]:
        return self.run_repo.get_by_id(run_id)

    def list_runs(self, limit: int = 50, offset: int = 0) -> List[RunModel]:
        return self.run_repo.list_runs(limit=limit, offset=offset)

    def get_businesses(
        self,
        run_id: str,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[BusinessModel], int]:
        return self.business_repo.list_by_run(
            run_id=run_id,
            page=page,
            page_size=page_size,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def get_business_detail(self, business_id: str) -> Optional[BusinessModel]:
        return self.business_repo.get_by_id(business_id)
