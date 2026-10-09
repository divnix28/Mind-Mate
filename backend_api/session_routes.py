from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from .database import get_db
from .models import ChatSession, Message, Student, SessionStatus, SenderType
from .connection_manager import manager
from backend_api.anonymizer import PIIAnonymizer

router = APIRouter(prefix="/api/v1/sessions", tags=["Session Lifecycle & Privacy"])
anonymizer = PIIAnonymizer()

from pydantic import BaseModel
from typing import Optional

class StartSessionRequest(BaseModel):
    student_id: Optional[int] = None

@router.post("/start")
def start_chat_session(payload: Optional[StartSessionRequest] = None, student_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Creates a new, isolated confidential student chat session in Tier 1 (LIVE_BOT).
    Guarantees privacy: counselors cannot view or join until risk triage escalation.
    """
    target_student_id = None
    if payload and payload.student_id:
        target_student_id = payload.student_id
    elif student_id:
        target_student_id = student_id

    student = None
    if target_student_id:
        student = db.query(Student).filter(Student.id == target_student_id).first()

    if not student:
        student = db.query(Student).first()

    if not student:
        student = Student(
            name="Divyanshu",
            reg_no="21BCE1001",
            email="divyanshu@campus.edu",
            block="BH-1",
            room="101",
            phone="+91-9876543211",
            password_hash="password123"
        )
        db.add(student)
        db.commit()
        db.refresh(student)

    new_session = ChatSession(
        student_id=student.id,
        status=SessionStatus.LIVE_BOT,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return {
        "status": "success",
        "session_id": new_session.id,
        "session_status": new_session.status.value,
        "created_at": new_session.created_at.isoformat(),
        "student": {
            "id": student.id,
            "name": student.name,
            "reg_no": student.reg_no,
            "email": student.email,
            "location": f"Block {student.block}, Room {student.room}"
        }
    }

@router.get("/{session_id}")
def get_session_info(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session #{session_id} not found.")
    
    return {
        "session_id": session.id,
        "status": session.status.value,
        "is_escalated": session.status != SessionStatus.LIVE_BOT,
        "created_at": session.created_at.isoformat() if session.created_at else None
    }

@router.get("/{session_id}/history")
def get_session_history(session_id: int, db: Session = Depends(get_db)):
    """
    Retrieves complete chronological message history for the student on reload/refresh.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session #{session_id} not found.")

    messages = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.timestamp.asc()).all()

    formatted_messages = []
    for msg in messages:
        formatted_messages.append({
            "id": msg.id,
            "sender": msg.sender_type.value,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
        })

    return {
        "session_id": session.id,
        "status": session.status.value,
        "messages": formatted_messages
    }

@router.post("/{session_id}/escalate")
async def request_counselor_escalation(session_id: int, db: Session = Depends(get_db)):
    """
    Voluntary escalation: student explicitly requests a human counselor.
    Transitions session from LIVE_BOT to AWAITING_COUNSELOR.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session #{session_id} not found.")

    if session.status == SessionStatus.LIVE_BOT:
        session.status = SessionStatus.AWAITING_COUNSELOR
        # Voluntary handoff has no prior trigger message (student clicked button).
        # Set escalation_msg_id to None so chatbot conversation is completely excluded.
        session.escalation_msg_id = None
        session.escalated_at = datetime.now(timezone.utc)
        db.commit()

        # Notify counselors
        await manager.broadcast_to_counselors({
            "event": "NEW_MODERATE_RISK",
            "session_id": session_id,
            "trigger": "Student voluntarily requested human counselor"
        })

    return {
        "status": "success",
        "session_id": session.id,
        "new_status": session.status.value
    }

@router.post("/{session_id}/return_to_bot")
async def return_to_bot_companion(session_id: int, db: Session = Depends(get_db)):
    """
    Returns session to Tier 1 AI companion mode, restoring active LLM responses,
    and immediately alerts the counselor that the counseling session is closed.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session #{session_id} not found.")

    session.status = SessionStatus.LIVE_BOT
    session.counselor_id = None
    session.escalation_msg_id = None
    session.escalated_at = None
    db.commit()

    # NOTIFY THE COUNSELOR IMMEDIATELY VIA WEBSOCKET
    await manager.send_to_role(session_id, "counselor", {
        "event": "STUDENT_RETURNED_TO_BOT",
        "session_id": session_id,
        "message": "The student has voluntarily switched back to Mind-Mate AI Companion mode. This counseling session is now concluded."
    })

    # Alert queue monitors to remove session from active triage queue
    await manager.broadcast_to_counselors({
        "event": "SESSION_RESOLVED",
        "session_id": session_id
    })

    return {
        "status": "success",
        "session_id": session.id,
        "new_status": session.status.value
    }
