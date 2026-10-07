"""WebSocket endpoints for real-time progress events."""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.workers.run_worker import register_ws_listener, unregister_ws_listener

router = APIRouter(tags=["WebSocket"])

@router.websocket("/ws/runs/{run_id}")
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
