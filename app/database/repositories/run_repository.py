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
        force: bool = False,
    ) -> Optional[RunModel]:
        run = self.get_by_id(run_id)
        if not run:
            return None

        # Validate lifecycle state transition unless forced
        if not force and run.status != status:
            from app.core.domain.enums import RunStatus, VALID_STATUS_TRANSITIONS
            try:
                curr_enum = RunStatus(run.status)
                new_enum = RunStatus(status)
                allowed = VALID_STATUS_TRANSITIONS.get(curr_enum, set())
                if new_enum not in allowed:
                    raise ValueError(f"Invalid run status transition from '{run.status}' to '{status}'")
            except ValueError as ve:
                if "Invalid run status transition" in str(ve):
                    raise

        run.status = status
        if started_at:
            run.started_at = started_at
        if completed_at:
            run.completed_at = completed_at
        if cancelled_at:
            run.cancelled_at = cancelled_at
        if error_message is not None:
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
        attempted: Optional[int] = None,
        duplicates: Optional[int] = None,
        error_count: Optional[int] = None,
    ) -> Optional[RunModel]:
        run = self.get_by_id(run_id)
        if not run:
            return None
        if discovered is not None:
            run.records_discovered = discovered
            run.total_google_records = discovered
        if attempted is not None:
            run.records_attempted = attempted
        if saved is not None:
            run.records_saved = saved
        if failed is not None:
            run.records_failed = failed
        if duplicates is not None:
            run.records_duplicates = duplicates
        if error_count is not None:
            run.error_count = error_count
        self.db.commit()
        self.db.refresh(run)
        return run

    def is_cancelled(self, run_id: str) -> bool:
        """Check if run is marked CANCELLED in SQLite database."""
        run = self.get_by_id(run_id)
        if not run:
            return True
        return run.status == "CANCELLED" or run.cancelled_at is not None

    def recover_stale_runs(self, message: str = "Execution was interrupted by process restart. Ready to resume from SQLite checkpoint.") -> int:
        """Finds orphaned RUNNING or QUEUED runs upon startup and marks them INTERRUPTED for checkpoint resumption."""
        stale = self.db.query(RunModel).filter(RunModel.status.in_(["RUNNING", "QUEUED"])).all()
        for r in stale:
            r.status = "INTERRUPTED"
            r.error_message = message
        if stale:
            self.db.commit()
        return len(stale)
