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

# CORS middleware for local Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router, prefix=settings.api_prefix)

# WebSocket endpoint for real-time run progress
@app.websocket("/ws/runs/{run_id}")
async def websocket_run_endpoint(websocket: WebSocket, run_id: str):
    await websocket.accept()

    async def send_event(data: dict):
        try:
            await websocket.send_text(json.dumps(data))
        except Exception:
            pass

    register_ws_listener(run_id, send_event)
    try:
        while True:
            # Keep connection open; receive ping/messages if any
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        unregister_ws_listener(run_id, send_event)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
