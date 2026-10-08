import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_sessions = {}
        self.counselor_connections = set()

    async def connect(self, websocket: WebSocket, session_id: int, role: str):
        await websocket.accept()
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {}
        
        # If an existing socket for this role exists and differs, close it cleanly
        if role in self.active_sessions[session_id]:
            old_ws = self.active_sessions[session_id][role]
            if old_ws != websocket:
                try:
                    await old_ws.close()
                except Exception:
                    pass

        self.active_sessions[session_id][role] = websocket
        if role == "counselor":
            self.counselor_connections.add(websocket)

    def disconnect(self, session_id: int, role: str, websocket: WebSocket = None):
        if session_id in self.active_sessions and role in self.active_sessions[session_id]:
            # ONLY remove if closing socket matches current active socket or none specified
            if websocket is None or self.active_sessions[session_id][role] == websocket:
                del self.active_sessions[session_id][role]
                if not self.active_sessions[session_id]:
                    del self.active_sessions[session_id]
        if role == "counselor" and websocket and websocket in self.counselor_connections:
            self.counselor_connections.discard(websocket)

    async def send_to_role(self, session_id: int, role: str, message: dict) -> bool:
        if session_id in self.active_sessions and role in self.active_sessions[session_id]:
            ws = self.active_sessions[session_id][role]
            try:
                await ws.send_json(message)
                return True
            except Exception as e:
                logger.warning(f"Failed to send to {role} in session {session_id}: {e}")
                self.disconnect(session_id, role, ws)
                return False
        return False

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
