from fastapi import FastAPI
from pydantic import BaseModel

from backend_api.anonymizer import PIIAnonymizer
from nlp_engine.risk_analyzer import RiskAnalyzer


app = FastAPI(
    title="Mind-Mate Risk Screening API",
    description="Non-diagnostic NLP processing and HITL routing."
)


# Initialize processing engines
anonymizer = PIIAnonymizer()
risk_analyzer = RiskAnalyzer()


class TextPayload(BaseModel):
    entry_id: str
    user_hash: str
    raw_text: str


@app.get("/")
def health_check():
    return {
        "status": "Active",
        "system": "Mind-Mate API Engine"
    }


@app.post("/api/v1/screen-text")
def screen_text(payload: TextPayload):

    # Step 1: Strip PII from incoming raw text
    sanitized_text = anonymizer.clean_text(
        payload.raw_text
    )

    # Step 2: Analyze ONLY the sanitized text
    analysis = risk_analyzer.analyze_entry(
        sanitized_text
    )

    # Step 3: Return the screening result
    return {
        "entry_id": payload.entry_id,
        "status": "Processed",
        "sanitized_text": sanitized_text,

        "risk_score": analysis["risk_score"],
        "risk_level": analysis["risk_level"],
        "linguistic_flags": analysis["linguistic_flags"],
        "requires_hitl": analysis["requires_hitl"]
    }