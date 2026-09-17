from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from datetime import datetime, timezone
import enum
from .database import Base

class ReviewStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    REFERRAL_RECOMMENDED = "REFERRAL_RECOMMENDED"
    DISMISSED = "DISMISSED"

class FlaggedEntry(Base):
    __tablename__ = "flagged_entries"

    entry_id = Column(Integer, primary_key=True, index=True)
    sanitized_text = Column(String, nullable=False)
    risk_score = Column(Float, nullable=False)
    status = Column(Enum(ReviewStatus), default=ReviewStatus.PENDING_REVIEW, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    counselor_notes = Column(String, nullable=True)