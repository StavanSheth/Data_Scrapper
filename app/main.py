"""Main FastAPI Application Entrypoint."""

import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.api.router import api_router
from app.database.engine import init_db
from app.workers.run_worker import register_ws_listener, unregister_ws_listener, TaskManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema
    init_db()
    # Recover any runs left in RUNNING/QUEUED from a prior crash or server restart
    TaskManager.recover_stale_runs()
    yield

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS middleware scoped to settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

from app.api.errors import register_exception_handlers
from app.api.routes.websocket import router as ws_router

# Register global exception handlers
register_exception_handlers(app)

# Mount API and WebSocket routers
app.include_router(api_router, prefix=settings.api_prefix)
app.include_router(ws_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
