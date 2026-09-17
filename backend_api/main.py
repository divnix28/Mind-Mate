from fastapi import FastAPI, Depends # <-- Added Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session   # <-- Added Session
from .database import engine, Base, get_db # <-- Added get_db
from .hitl_routes import router as hitl_router
from .models import FlaggedEntry, ReviewStatus # <-- Added our models

from backend_api.anonymizer import PIIAnonymizer
from nlp_engine.risk_analyzer import RiskAnalyzer

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Mind-Mate Risk Screening API",
    description="Non-diagnostic NLP processing and HITL routing."
)

anonymizer = PIIAnonymizer()
risk_analyzer = RiskAnalyzer()

class TextPayload(BaseModel):
    entry_id: str
    user_hash: str
    raw_text: str

@app.get("/")
def health_check():
    return {"status": "Active", "system": "Mind-Mate API Engine"}

# Inject the DB session here
@app.post("/api/v1/screen-text")
def screen_text(payload: TextPayload, db: Session = Depends(get_db)):

    # Step 1: Strip PII from incoming raw text
    sanitized_text = anonymizer.clean_text(payload.raw_text)

    # Step 2: Analyze ONLY the sanitized text
    analysis = risk_analyzer.analyze_entry(sanitized_text)

    # Step 3: DATABASE PERSISTENCE (If high risk, save to DB)
    if analysis["requires_hitl"]:
        new_flagged_entry = FlaggedEntry(
            sanitized_text=sanitized_text,
            risk_score=analysis["risk_score"],
            status=ReviewStatus.PENDING_REVIEW
        )
        db.add(new_flagged_entry)
        db.commit()

    # Step 4: Return the screening result
    return {
        "entry_id": payload.entry_id,
        "status": "Processed",
        "sanitized_text": sanitized_text,
        "risk_score": analysis["risk_score"],
        "risk_level": analysis["risk_level"],
        "linguistic_flags": analysis["linguistic_flags"],
        "requires_hitl": analysis["requires_hitl"]
    }

app.include_router(hitl_router)