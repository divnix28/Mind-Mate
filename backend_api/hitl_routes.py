from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import get_db
from .models import ChatSession, Student, Message, SessionStatus, SenderType
from .connection_manager import manager
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
        # Fetch the trigger message or most recent student message to display as triage preview
        preview = "Flagged for counselor review"
        trigger_msg = None
        if s.escalation_msg_id:
            trigger_msg = db.query(Message).filter(Message.id == s.escalation_msg_id).first()
        
        if not trigger_msg:
            trigger_msg = db.query(Message).filter(
                Message.session_id == s.id,
                Message.sender_type == SenderType.STUDENT
            ).order_by(Message.timestamp.desc()).first()

        if trigger_msg:
            # Scrub preview text for counselor privacy compliance
            preview = anonymizer.clean_text(trigger_msg.content)
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

@router.get("/session/{session_id}/transcript")
def get_counselor_session_transcript(session_id: int, db: Session = Depends(get_db)):
    """
    CRITICAL PRIVACY ENFORCEMENT:
    A counselor must NEVER see the student's private AI companion banter (Tier 1).
    This endpoint ONLY returns:
    1. The scrubbed escalation trigger summary
    2. Messages exchanged DURING/AFTER escalation (between student and counselor)
    All student messages returned here are strictly scrubbed using Presidio PIIAnonymizer.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    if session.status == SessionStatus.LIVE_BOT:
        raise HTTPException(
            status_code=403, 
            detail="Access Denied: Session is in confidential Tier 1 AI companion mode."
        )

    # 1. Determine scrubbed escalation trigger
    trigger_text = "Student requested counselor intervention"
    start_msg_id = session.escalation_msg_id

    if start_msg_id:
        trigger_msg = db.query(Message).filter(Message.id == start_msg_id).first()
        if trigger_msg:
            trigger_text = anonymizer.clean_text(trigger_msg.content)
    else:
        # Fallback: look for the last student message before the first counselor message
        first_counselor_msg = db.query(Message).filter(
            Message.session_id == session_id,
            Message.sender_type == SenderType.COUNSELOR
        ).order_by(Message.timestamp.asc()).first()
        
        if first_counselor_msg:
            trigger_candidate = db.query(Message).filter(
                Message.session_id == session_id,
                Message.sender_type == SenderType.STUDENT,
                Message.timestamp <= first_counselor_msg.timestamp
            ).order_by(Message.timestamp.desc()).first()
            if trigger_candidate:
                trigger_text = anonymizer.clean_text(trigger_candidate.content)
                start_msg_id = trigger_candidate.id
        else:
            # If no counselor message yet, find the most recent student message that triggered awaiting
            last_stud = db.query(Message).filter(
                Message.session_id == session_id,
                Message.sender_type == SenderType.STUDENT
            ).order_by(Message.timestamp.desc()).first()
            if last_stud:
                trigger_text = anonymizer.clean_text(last_stud.content)
                start_msg_id = last_stud.id

    # 2. Query only messages exchanged during the counselor phase
    query = db.query(Message).filter(Message.session_id == session_id)
    if start_msg_id:
        # Start immediately AFTER the trigger message
        query = query.filter(Message.id > start_msg_id)
    
    raw_messages = query.order_by(Message.timestamp.asc()).all()

    formatted = []
    for msg in raw_messages:
        # Strictly omit any private BOT messages
        if msg.sender_type == SenderType.BOT:
            continue
        
        # Scrub all student messages before counselor ever sees them
        content = anonymizer.clean_text(msg.content) if msg.sender_type == SenderType.STUDENT else msg.content
        formatted.append({
            "id": msg.id,
            "sender": msg.sender_type.value,
            "content": content,
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
        })

    return {
        "session_id": session.id,
        "status": session.status.value,
        "escalation_trigger": trigger_text,
        "messages": formatted
    }

@router.post("/resolve/{session_id}")
async def resolve_counselor_session(session_id: int, db: Session = Depends(get_db)):
    """
    Counselor marks intervention resolved, de-escalating session back to LIVE_BOT.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    session.status = SessionStatus.LIVE_BOT
    db.commit()

    # Inform student via WebSocket
    await manager.send_to_role(session_id, "student", {
        "sender": "SYSTEM",
        "content": "Counseling session completed. Returned to Mind-Mate AI Companion mode."
    })

    # Inform counselor
    await manager.send_to_role(session_id, "counselor", {
        "event": "STUDENT_RETURNED_TO_BOT",
        "session_id": session_id,
        "message": "Session resolved and student safely returned to AI companion."
    })

    await manager.broadcast_to_counselors({
        "event": "SESSION_RESOLVED",
        "session_id": session_id
    })

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