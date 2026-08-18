from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Mind-Mate Risk Screening API", description="Non-diagnostic NLP processing and HITL routing.")

# Define the expected input payload from a journal or chat entry
class TextPayload(BaseModel):
    entry_id: str
    user_hash: str  #Not a real name or student ID, for privacy
    raw_text: str

@app.get("/")
def health_check():
    return {"status": "Active", "system": "Mind-Mate API Engine"}

@app.post("/api/v1/screen-text")
def screen_text(payload: TextPayload):
    """
    Pipeline Workflow:
    1. Send raw_text to Member 2's PII Anonymizer.
    2. Send clean_text to Member 3's NLP Model (MentalBERT).
    3. Return risk_score and hitl_flag to frontend.
    """
    
    # MOCK RESPONSE
    return {
        "entry_id": payload.entry_id,
        "status": "Processed",
        "risk_score": 0.85,             # Mock high-risk score
        "requires_human_review": True   # Flags it for Member 5's dashboard
    }