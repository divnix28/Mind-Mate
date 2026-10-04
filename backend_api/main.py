import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

load_dotenv()

from .database import engine, Base, get_db
from .hitl_routes import router as hitl_router
from .models import ChatSession, Message, SessionStatus, SenderType
from backend_api.anonymizer import PIIAnonymizer
from nlp_engine.risk_analyzer import RiskAnalyzer

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Mind-Mate Real-Time Engine",
    description="3-Tier Mental Health Triage and WebSocket Routing"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

anonymizer = PIIAnonymizer()
risk_analyzer = RiskAnalyzer()

# --- Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_sessions = {}

    async def connect(self, websocket: WebSocket, session_id: int, role: str):
        await websocket.accept()
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {}
        self.active_sessions[session_id][role] = websocket

    def disconnect(self, session_id: int, role: str):
        if session_id in self.active_sessions and role in self.active_sessions[session_id]:
            del self.active_sessions[session_id][role]

    async def send_to_role(self, session_id: int, role: str, message: dict):
        if session_id in self.active_sessions and role in self.active_sessions[session_id]:
            await self.active_sessions[session_id][role].send_json(message)

manager = ConnectionManager()

@app.get("/api/v1/health")
def health_check():
    return {"status": "Active", "system": "Mind-Mate API Engine"}

# --- Tier 1 & 2: Student Portal ---
@app.websocket("/ws/student/{session_id}")
async def student_chat_endpoint(websocket: WebSocket, session_id: int, db: Session = Depends(get_db)):
    await manager.connect(websocket, session_id, "student")
    
    chat_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not chat_session:
        await websocket.close(code=1008)
        return

    try:
        while True:
            data = await websocket.receive_text()
            
            # Save raw message
            new_msg = Message(session_id=session_id, sender_type=SenderType.STUDENT, content=data)
            db.add(new_msg)
            db.commit()

            # Pass through Member 2's privacy scrubber
            scrubbed_text = anonymizer.clean_text(data)

            db.refresh(chat_session)
            
            if chat_session.status == SessionStatus.LIVE_BOT:
                # Query DB to build chat history for Groq context
                past_messages = db.query(Message).filter(
                    Message.session_id == session_id,
                    Message.id != new_msg.id
                ).order_by(Message.timestamp).all()
                
                chat_history = []
                for msg in past_messages:
                    role = "user" if msg.sender_type == SenderType.STUDENT else "assistant"
                    safe_content = anonymizer.clean_text(msg.content) if role == "user" else msg.content
                    chat_history.append({"role": role, "content": safe_content})
                    
                # Await Member 3's LLM evaluation
                llm_response = await risk_analyzer.generate_triage_response(chat_history, scrubbed_text)
                
                if llm_response["risk_tier"] == 1:
                    bot_msg = Message(session_id=session_id, sender_type=SenderType.BOT, content=llm_response["bot_reply"])
                    db.add(bot_msg)
                    db.commit()
                    await websocket.send_json({"sender": "BOT", "content": llm_response["bot_reply"]})
                else:
                    # Halt bot and route to Human (Tier 2/3)
                    chat_session.status = SessionStatus.AWAITING_COUNSELOR
                    db.commit()
                    await websocket.send_json({"sender": "SYSTEM", "content": "Routing you to a human counselor safely and anonymously..."})
                    await manager.send_to_role(session_id, "counselor", {"event": "NEW_MODERATE_RISK"})

            elif chat_session.status == SessionStatus.LIVE_COUNSELOR:
                await manager.send_to_role(session_id, "counselor", {"sender": "STUDENT", "content": scrubbed_text})
            
            elif chat_session.status == SessionStatus.CRITICAL_SOS:
                await websocket.send_json({"sender": "SYSTEM", "content": "Help is on the way. Please stay right where you are."})

    except WebSocketDisconnect:
        manager.disconnect(session_id, "student")

# --- Tier 2: Counselor Portal ---
@app.websocket("/ws/counselor/{session_id}")
async def counselor_chat_endpoint(websocket: WebSocket, session_id: int, db: Session = Depends(get_db)):
    await manager.connect(websocket, session_id, "counselor")
    
    chat_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not chat_session:
        await websocket.close(code=1008)
        return

    try:
        while True:
            data = await websocket.receive_text()
            db.refresh(chat_session)

            if chat_session.status == SessionStatus.AWAITING_COUNSELOR:
                chat_session.status = SessionStatus.LIVE_COUNSELOR
                db.commit()

            if chat_session.status == SessionStatus.LIVE_COUNSELOR:
                new_msg = Message(session_id=session_id, sender_type=SenderType.COUNSELOR, content=data)
                db.add(new_msg)
                db.commit()
                await manager.send_to_role(session_id, "student", {"sender": "COUNSELOR", "content": data})

    except WebSocketDisconnect:
        manager.disconnect(session_id, "counselor")

app.include_router(hitl_router)
if os.path.exists("hitl_dashboard"):
    app.mount("/", StaticFiles(directory="hitl_dashboard", html=True), name="dashboard")