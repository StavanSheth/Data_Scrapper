"""Repository for Run entities."""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database.models import RunModel

class RunRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, run: RunModel) -> RunModel:
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_by_id(self, run_id: str) -> Optional[RunModel]:
        return self.db.query(RunModel).filter(RunModel.id == run_id).first()

    def list_runs(self, limit: int = 50, offset: int = 0) -> List[RunModel]:
        return (
            self.db.query(RunModel)
            .order_by(desc(RunModel.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_runs(self) -> int:
        return self.db.query(RunModel).count()

    def update_status(
        self,
        run_id: str,
        status: str,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        cancelled_at: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[RunModel]:
        run = self.get_by_id(run_id)
        if not run:
            return None
        run.status = status
        if started_at:
            run.started_at = started_at
        if completed_at:
            run.completed_at = completed_at
        if cancelled_at:
            run.cancelled_at = cancelled_at
        if error_message:
            run.error_message = error_message
        self.db.commit()
        self.db.refresh(run)
        return run

    def update_counts(
        self,
        run_id: str,
        discovered: Optional[int] = None,
        saved: Optional[int] = None,
        failed: Optional[int] = None,
        error_count: Optional[int] = None,
    ) -> Optional[RunModel]:
        run = self.get_by_id(run_id)
        if not run:
            return None
        if discovered is not None:
            run.records_discovered = discovered
            run.total_google_records = discovered
        if saved is not None:
            run.records_saved = saved
        if failed is not None:
            run.records_failed = failed
        if error_count is not None:
            run.error_count = error_count
        self.db.commit()
        self.db.refresh(run)
        return run
