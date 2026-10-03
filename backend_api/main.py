import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

load_dotenv()

from .database import engine, Base, get_db
from .hitl_routes import router as hitl_router
from .models import FlaggedEntry, ReviewStatus
from backend_api.anonymizer import PIIAnonymizer
from nlp_engine.risk_analyzer import RiskAnalyzer

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Mind-Mate Risk Screening API",
    description="3-Tier Mental Health Triage and WebSocket Routing"
)

# CORS Middleware 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

anonymizer = PIIAnonymizer()
risk_analyzer = RiskAnalyzer()

class TextPayload(BaseModel):
    entry_id: str
    user_hash: str
    raw_text: str

@app.get("/api/v1/health")
def health_check():
    return {"status": "Active", "system": "Mind-Mate API Engine"}

# Legacy REST Route 
@app.post("/api/v1/screen-text")
def screen_text(payload: TextPayload, db: Session = Depends(get_db)):
    sanitized_text = anonymizer.clean_text(payload.raw_text)
    analysis = risk_analyzer.analyze_entry(sanitized_text)

    if analysis["requires_hitl"]:
        new_flagged_entry = FlaggedEntry(
            sanitized_text=sanitized_text,
            risk_score=analysis["risk_score"],
            status=ReviewStatus.PENDING_REVIEW
        )
        db.add(new_flagged_entry)
        db.commit()

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
app.mount("/", StaticFiles(directory="hitl_dashboard", html=True), name="dashboard")
