import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

load_dotenv()

from .database import engine, Base, get_db
from .connection_manager import manager
from .hitl_routes import router as hitl_router
from .session_routes import router as session_router
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

@app.get("/api/v1/health")
def health_check():
    return {"status": "Active", "system": "Mind-Mate API Engine"}

# --- Tier 1 & 2: Student Portal ---
@app.websocket("/ws/student/{session_id}")
async def student_chat_endpoint(websocket: WebSocket, session_id: int, db: Session = Depends(get_db)):
    chat_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not chat_session:
        await websocket.accept()
        await websocket.send_json({"sender": "SYSTEM", "content": "Error: Chat session not found."})
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, session_id, "student")
    
    # Sync initial state to student client
    await websocket.send_json({
        "event": "SESSION_STATE",
        "status": chat_session.status.value,
        "session_id": session_id
    })

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
                    
                # Await LLM evaluation
                llm_response = await risk_analyzer.generate_triage_response(chat_history, scrubbed_text)
                
                if llm_response["risk_tier"] == 1:
                    # Scrub bot reply as well so it never mirrors student names or identifiers
                    safe_bot_reply = anonymizer.clean_text(llm_response["bot_reply"])
                    bot_msg = Message(session_id=session_id, sender_type=SenderType.BOT, content=safe_bot_reply)
                    db.add(bot_msg)
                    db.commit()
                    await websocket.send_json({"sender": "BOT", "content": safe_bot_reply})
                else:
                    # Halt bot and route to Human (Tier 2/3)
                    chat_session.status = SessionStatus.AWAITING_COUNSELOR
                    chat_session.escalation_msg_id = new_msg.id
                    chat_session.escalated_at = datetime.now(timezone.utc)
                    db.commit()
                    await websocket.send_json({
                        "sender": "SYSTEM",
                        "content": "Routing you to a human counselor safely and anonymously..."
                    })
                    await manager.send_to_role(session_id, "counselor", {
                        "event": "NEW_MODERATE_RISK", 
                        "session_id": session_id,
                        "trigger": scrubbed_text
                    })
                    await manager.broadcast_to_counselors({
                        "event": "NEW_MODERATE_RISK", 
                        "session_id": session_id,
                        "trigger": scrubbed_text
                    })

            elif chat_session.status == SessionStatus.AWAITING_COUNSELOR:
                # Waiting for a counselor to claim the room
                await websocket.send_json({
                    "sender": "SYSTEM",
                    "content": "Your request is in the counselor queue. A campus counselor will join your session momentarily."
                })
                await manager.send_to_role(session_id, "counselor", {"sender": "STUDENT", "content": scrubbed_text})
                await manager.broadcast_to_counselors({
                    "event": "NEW_MODERATE_RISK", 
                    "session_id": session_id,
                    "trigger": scrubbed_text
                })

            elif chat_session.status == SessionStatus.LIVE_COUNSELOR:
                # Active counselor session
                if session_id in manager.active_sessions and "counselor" in manager.active_sessions[session_id]:
                    await manager.send_to_role(session_id, "counselor", {"sender": "STUDENT", "content": scrubbed_text})
                else:
                    await websocket.send_json({
                        "sender": "SYSTEM",
                        "content": "Counselor is currently reconnecting. Your message has been safely logged."
                    })

            elif chat_session.status == SessionStatus.CRITICAL_SOS:
                await websocket.send_json({"sender": "SYSTEM", "content": "Help is on the way. Please stay right where you are."})

    except WebSocketDisconnect:
        manager.disconnect(session_id, "student", websocket)

# --- Tier 2: Counselor Portal ---
@app.websocket("/ws/counselor/{session_id}")
async def counselor_chat_endpoint(websocket: WebSocket, session_id: int, db: Session = Depends(get_db)):
    chat_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not chat_session:
        await websocket.accept()
        await websocket.send_json({
            "event": "ACCESS_DENIED",
            "error": "SESSION_NOT_FOUND",
            "detail": f"Session #{session_id} does not exist in the database."
        })
        await websocket.close(code=1008)
        return

    # STRICT PRIVACY ENFORCEMENT:
    # A counselor CANNOT join an unescalated Tier 1 private AI companion session.
    if chat_session.status == SessionStatus.LIVE_BOT:
        await websocket.accept()
        await websocket.send_json({
            "event": "ACCESS_DENIED",
            "error": "UNAUTHORIZED_ACCESS",
            "detail": f"Access Denied: Session #{session_id} is in confidential AI companion mode (Tier 1). Counselors cannot join unescalated student chats."
        })
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, session_id, "counselor")
    
    # If session was awaiting counselor, counselor claiming it sets it to LIVE_COUNSELOR
    if chat_session.status == SessionStatus.AWAITING_COUNSELOR:
        chat_session.status = SessionStatus.LIVE_COUNSELOR
        db.commit()
        await manager.send_to_role(session_id, "student", {
            "sender": "SYSTEM",
            "content": "A licensed campus counselor has joined the session."
        })

    try:
        while True:
            data = await websocket.receive_text()
            db.refresh(chat_session)

            if chat_session.status == SessionStatus.LIVE_COUNSELOR:
                new_msg = Message(session_id=session_id, sender_type=SenderType.COUNSELOR, content=data)
                db.add(new_msg)
                db.commit()
                await manager.send_to_role(session_id, "student", {"sender": "COUNSELOR", "content": data})

    except WebSocketDisconnect:
        manager.disconnect(session_id, "counselor", websocket)

# Register Sub-Routers
app.include_router(hitl_router)
app.include_router(session_router)

# Mount Dashboard Frontend
if os.path.exists("hitl_dashboard"):
    app.mount("/", StaticFiles(directory="hitl_dashboard", html=True), name="dashboard")