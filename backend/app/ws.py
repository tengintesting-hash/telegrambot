import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

from app.api import validate_init_data

ws_router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[int, set[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        connections = self.active.get(user_id)
        if connections:
            connections.discard(websocket)
            if not connections:
                self.active.pop(user_id, None)

    async def send_balance(self, user_id: int, balance: str) -> None:
        payload = json.dumps({"balance": balance})
        for ws in list(self.active.get(user_id, set())):
            await ws.send_text(payload)


manager = ConnectionManager()


@ws_router.websocket("/ws/user/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, initData: str | None = None) -> None:
    if not initData:
        await websocket.close(code=1008)
        return
    data = validate_init_data(initData)
    user_data = json.loads(data["user"])
    if int(user_data["id"]) != user_id:
        await websocket.close(code=1008)
        return
    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
