"""Central API router."""

from fastapi import APIRouter
from app.api.routes import health, runs, businesses

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(runs.router)
api_router.include_router(businesses.router)
