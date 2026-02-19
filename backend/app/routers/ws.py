"""WebSocket endpoint for real-time filing broadcasts."""

from __future__ import annotations

import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

log = logging.getLogger("secpulse.ws")

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts messages."""

    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)
        log.info("Client connected (%d total)", len(self.active))

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)
        log.info("Client disconnected (%d total)", len(self.active))

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.discard(ws)


manager = ConnectionManager()


@router.websocket("/ws/filings")
async def filings_ws(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; client can send filter preferences
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
