from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from .database import get_db
from .models import FlaggedEntry, ReviewStatus

router = APIRouter(prefix="/api/v1/hitl", tags=["Human-in-the-Loop"])

class FlaggedEntryResponse(BaseModel):
    entry_id: int
    sanitized_text: str
    risk_score: float
    status: ReviewStatus
    created_at: datetime
    counselor_notes: Optional[str] = None
    class Config:
        from_attributes = True

class ReviewActionRequest(BaseModel):
    entry_id: int
    status: ReviewStatus
    notes: Optional[str] = None

@router.get("/pending", response_model=List[FlaggedEntryResponse])
def get_pending_entries(db: Session = Depends(get_db)):
    return db.query(FlaggedEntry).filter(FlaggedEntry.status == ReviewStatus.PENDING_REVIEW).all()

@router.post("/review", response_model=FlaggedEntryResponse)
def submit_counselor_review(action: ReviewActionRequest, db: Session = Depends(get_db)):
    entry = db.query(FlaggedEntry).filter(FlaggedEntry.entry_id == action.entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found.")
    
    entry.status = action.status
    if action.notes:
        entry.counselor_notes = action.notes
        
    db.commit()
    db.refresh(entry)
    return entry