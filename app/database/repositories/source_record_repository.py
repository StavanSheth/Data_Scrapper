"""Repository for SourceRecord entities."""

from typing import Optional, List
from sqlalchemy.orm import Session
from app.database.models import SourceRecordModel

class SourceRecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, record: SourceRecordModel) -> SourceRecordModel:
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_by_id(self, record_id: str) -> Optional[SourceRecordModel]:
        return self.db.query(SourceRecordModel).filter(SourceRecordModel.id == record_id).first()

    def get_by_external_id(self, run_id: str, external_id: str) -> Optional[SourceRecordModel]:
        return (
            self.db.query(SourceRecordModel)
            .filter(
                SourceRecordModel.run_id == run_id,
                SourceRecordModel.external_id == external_id
            )
            .first()
        )

    def list_by_run_id(self, run_id: str, limit: int = 100, offset: int = 0) -> List[SourceRecordModel]:
        return (
            self.db.query(SourceRecordModel)
            .filter(SourceRecordModel.run_id == run_id)
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_existing_identifiers_for_run(self, run_id: str) -> tuple[set[str], set[str]]:
        """Returns sets of (place_ids, source_urls) previously discovered for checkpoint resumption."""
        records = (
            self.db.query(SourceRecordModel.external_id, SourceRecordModel.source_url)
            .filter(SourceRecordModel.run_id == run_id)
            .all()
        )
        place_ids = {r[0] for r in records if r[0]}
        urls = {r[1] for r in records if r[1]}
        return place_ids, urls
