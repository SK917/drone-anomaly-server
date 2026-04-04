import asyncio
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import server_engine.state as state

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if not self.active_connections:
            print("[SESSION] Last client disconnected. Clearing anomaly logs.")
            state.anomalies_list.clear()
            state.anomalies_by_track_id.clear()
            state.seen_anomaly_ids.clear()

    async def broadcast(self, message: dict):
        stale_connections: List[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                stale_connections.append(connection)

        for connection in stale_connections:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

manager = ConnectionManager()

@router.websocket("/updates")
async def websocket_updates(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while not state.stop_event.is_set():
            await websocket.receive_text()
    except (WebSocketDisconnect, asyncio.CancelledError):
        manager.disconnect(websocket)
    finally:
        manager.disconnect(websocket)
