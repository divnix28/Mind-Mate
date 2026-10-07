from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_sessions = {}
        self.counselor_connections = set()

    async def connect(self, websocket: WebSocket, session_id: int, role: str):
        await websocket.accept()
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {}
        self.active_sessions[session_id][role] = websocket
        if role == "counselor":
            self.counselor_connections.add(websocket)

    def disconnect(self, session_id: int, role: str, websocket: WebSocket = None):
        if session_id in self.active_sessions and role in self.active_sessions[session_id]:
            del self.active_sessions[session_id][role]
            if not self.active_sessions[session_id]:
                del self.active_sessions[session_id]
        if role == "counselor" and websocket and websocket in self.counselor_connections:
            self.counselor_connections.remove(websocket)

    async def send_to_role(self, session_id: int, role: str, message: dict):
        if session_id in self.active_sessions and role in self.active_sessions[session_id]:
            try:
                await self.active_sessions[session_id][role].send_json(message)
            except Exception:
                pass

    async def broadcast_to_counselors(self, message: dict):
        dead_sockets = []
        for ws in list(self.counselor_connections):
            try:
                await ws.send_json(message)
            except Exception:
                dead_sockets.append(ws)
        for dead in dead_sockets:
            self.counselor_connections.discard(dead)

manager = ConnectionManager()
