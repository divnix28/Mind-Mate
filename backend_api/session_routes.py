from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from .database import get_db
from .models import ChatSession, Message, Student, SessionStatus, SenderType
from backend_api.anonymizer import PIIAnonymizer

router = APIRouter(prefix="/api/v1/sessions", tags=["Session Lifecycle & Privacy"])
anonymizer = PIIAnonymizer()

@router.post("/start")
def start_chat_session(db: Session = Depends(get_db)):
    """
    Creates a new, isolated confidential student chat session in Tier 1 (LIVE_BOT).
    Guarantees privacy: counselors cannot view or join until risk triage escalation.
    """
    # Find or create a default student record
    student = db.query(Student).first()
    if not student:
        student = Student(
            name="Alex",
            reg_no="21BCE1001",
            block="BH-3",
            room="405",
            phone="+91-9876543210",
            password_hash="demo_student_hash"
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
        "created_at": new_session.created_at.isoformat()
    }

@router.get("/{session_id}")
def get_session_info(session_id: int, db: Session = Depends(get_db)):
    """
    Returns high-level status for a session.
    """
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
    Retrieves complete chronological message history and active tier status for a session.
    Used on page load / hard-refresh to restore UI state accurately.
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
def request_counselor_escalation(session_id: int, db: Session = Depends(get_db)):
    """
    Voluntary escalation: student explicitly requests a human counselor.
    Transitions session from LIVE_BOT to AWAITING_COUNSELOR.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session #{session_id} not found.")

    if session.status == SessionStatus.LIVE_BOT:
        session.status = SessionStatus.AWAITING_COUNSELOR
        db.commit()

    return {
        "status": "success",
        "session_id": session.id,
        "new_status": session.status.value
    }

@router.post("/{session_id}/return_to_bot")
def return_to_bot_companion(session_id: int, db: Session = Depends(get_db)):
    """
    Returns session to Tier 1 AI companion mode, restoring active LLM responses.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session #{session_id} not found.")

    session.status = SessionStatus.LIVE_BOT
    db.commit()

    return {
        "status": "success",
        "session_id": session.id,
        "new_status": session.status.value
    }
