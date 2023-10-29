import fastapi

class WebSocketManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: fastapi.WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: fastapi.WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: fastapi.WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, data: str):
        for connection in self.active_connections:
            await connection.send_text(data)
