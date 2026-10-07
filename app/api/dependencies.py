"""FastAPI dependencies."""

from fastapi import Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.core.services.run_service import RunService

def get_run_service(db: Session = Depends(get_db)) -> RunService:
    return RunService(db)
