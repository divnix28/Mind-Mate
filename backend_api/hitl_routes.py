from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import get_db
from .models import ChatSession, Student, Message, SessionStatus, SenderType
from backend_api.anonymizer import PIIAnonymizer

router = APIRouter(prefix="/api/v1/hitl", tags=["Human-in-the-Loop"])
anonymizer = PIIAnonymizer()

@router.get("/queue")
def get_escalation_queue(db: Session = Depends(get_db)):
    """
    Returns only sessions that require counselor intervention or are in active clinical triage.
    STRICT PRIVACY RULE: Tier 1 private AI sessions (LIVE_BOT) are NEVER returned in this queue.
    """
    escalated_statuses = [
        SessionStatus.AWAITING_COUNSELOR,
        SessionStatus.LIVE_COUNSELOR,
        SessionStatus.CRITICAL_SOS
    ]

    sessions = db.query(ChatSession).filter(
        ChatSession.status.in_(escalated_statuses)
    ).order_by(ChatSession.created_at.desc()).all()

    queue_items = []
    for s in sessions:
        # Fetch the most recent message from student to display as triage preview
        last_student_msg = db.query(Message).filter(
            Message.session_id == s.id,
            Message.sender_type == SenderType.STUDENT
        ).order_by(Message.timestamp.desc()).first()

        preview = "Flagged for counselor review"
        if last_student_msg:
            # Scrub preview text for counselor privacy compliance
            preview = anonymizer.clean_text(last_student_msg.content)
            if len(preview) > 60:
                preview = preview[:57] + "..."

        msg_count = db.query(Message).filter(Message.session_id == s.id).count()

        queue_items.append({
            "id": s.id,
            "status": s.status.value,
            "preview": preview,
            "message_count": msg_count,
            "created_at": s.created_at.isoformat() if s.created_at else None
        })

    return queue_items

@router.post("/resolve/{session_id}")
def resolve_counselor_session(session_id: int, db: Session = Depends(get_db)):
    """
    Counselor marks intervention resolved, de-escalating session back to LIVE_BOT.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    session.status = SessionStatus.LIVE_BOT
    db.commit()

    return {
        "status": "success",
        "message": f"Session #{session_id} resolved and returned to AI companion mode."
    }

@router.post("/sos/unmask/{session_id}")
def trigger_sos_unmask(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    
    student = db.query(Student).filter(Student.id == session.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student record not found.")

    # Override the chat state to halt all normal bot/chat operations
    session.status = SessionStatus.CRITICAL_SOS
    db.commit()

    # Return unredacted data for emergency dispatch
    return {
        "alert": "CRITICAL SOS TRIGGERED",
        "student_name": student.name,
        "reg_no": student.reg_no,
        "location": f"Block {student.block}, Room {student.room}",
        "phone": student.phone
    }