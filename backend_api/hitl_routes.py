from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import get_db
from .models import ChatSession, Student, SessionStatus

router = APIRouter(prefix="/api/v1/hitl", tags=["Human-in-the-Loop"])

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