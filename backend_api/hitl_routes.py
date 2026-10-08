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
    This endpoint returns all student and counselor messages for escalated sessions.
    All student messages returned here are strictly scrubbed using Presidio PIIAnonymizer.
    Private AI bot banter is completely excluded.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    if session.status == SessionStatus.LIVE_BOT:
        raise HTTPException(
            status_code=403, 
            detail="Access Denied: Session is in confidential Tier 1 AI companion mode."
        )

    # Return all student & counselor messages for this session
    messages = db.query(Message).filter(
        Message.session_id == session_id,
        Message.sender_type.in_([SenderType.STUDENT, SenderType.COUNSELOR])
    ).order_by(Message.timestamp.asc()).all()

    formatted = []
    for msg in messages:
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
        "messages": formatted
    }

@router.post("/sos/close/{session_id}")
async def close_sos_incident(session_id: int, db: Session = Depends(get_db)):
    """
    Counselor stops the critical SOS alarm / protocol when the emergency matter is closed or resolved.
    Transitions session status to LIVE_COUNSELOR so communication can continue normally.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    session.status = SessionStatus.LIVE_COUNSELOR
    db.commit()

    # Inform student
    await manager.send_to_role(session_id, "student", {
        "sender": "SYSTEM",
        "event": "SOS_RESOLVED",
        "content": "The emergency SOS protocol has been closed by your counselor. You remain in safe communication."
    })

    # Broadcast to all counselors to update queue and active counselor console
    await manager.broadcast_to_counselors({
        "event": "SOS_RESOLVED",
        "session_id": session_id,
        "message": "Critical SOS closed. Emergency matter marked safe and resolved."
    })

    return {
        "status": "success",
        "session_id": session_id,
        "new_status": session.status.value,
        "message": f"Critical SOS for session #{session_id} has been stopped and marked safe."
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

@router.get("/sos/details/{session_id}")
def get_sos_details(session_id: int, db: Session = Depends(get_db)):
    """
    Read-only endpoint to fetch unmasked student dispatch details without triggering any alerts or events.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    
    student = db.query(Student).filter(Student.id == session.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student record not found.")

    return {
        "student_name": student.name,
        "reg_no": student.reg_no,
        "location": f"Block {student.block}, Room {student.room}",
        "phone": student.phone,
        "email": student.email or "N/A"
    }

@router.post("/sos/unmask/{session_id}")
async def trigger_sos_unmask(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    
    student = db.query(Student).filter(Student.id == session.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student record not found.")

    # Only broadcast dispatch notifications if session is not already in CRITICAL_SOS
    if session.status != SessionStatus.CRITICAL_SOS:
        session.status = SessionStatus.CRITICAL_SOS
        db.commit()

        # Alert the student via WebSocket ONCE
        await manager.send_to_role(session_id, "student", {
            "event": "SOS_DISPATCH_TRIGGERED",
            "sender": "SYSTEM",
            "content": "Campus emergency team has been alerted for physical support. Your counselor remains live with you in this chat."
        })

        # Broadcast to all counselors ONCE
        await manager.broadcast_to_counselors({
            "event": "CRITICAL_SOS_TRIGGERED",
            "session_id": session_id,
            "message": f"Emergency campus dispatch unmasked for Session #{session_id}."
        })

    # Return unredacted data for emergency dispatch
    return {
        "alert": "CRITICAL SOS TRIGGERED",
        "student_name": student.name,
        "reg_no": student.reg_no,
        "location": f"Block {student.block}, Room {student.room}",
        "phone": student.phone,
        "email": student.email or "N/A"
    }