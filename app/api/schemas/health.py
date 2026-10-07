"""Health check schema."""

from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    timestamp: str
