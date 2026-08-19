from fastapi import FastAPI
from pydantic import BaseModel
from anonymizer import PIIAnonymizer

app = FastAPI(
    title="Mind-Mate Risk Screening API", 
    description="Non-diagnostic NLP processing and HITL routing."
)

# Initialize the PII scrubber engine
anonymizer = PIIAnonymizer()

class TextPayload(BaseModel):
    entry_id: str
    user_hash: str
    raw_text: str

@app.get("/")
def health_check():
    return {"status": "Active", "system": "Mind-Mate API Engine"}

@app.post("/api/v1/screen-text")
def screen_text(payload: TextPayload):
    # Step 1: Strip PII from incoming raw text
    sanitized_text = anonymizer.clean_text(payload.raw_text)
    
    # Step 2: Pass sanitized text to risk engine
    return {
        "entry_id": payload.entry_id,
        "status": "Processed",
        "sanitized_text": sanitized_text,
        "risk_score": 0.85,
        "requires_human_review": True
    }