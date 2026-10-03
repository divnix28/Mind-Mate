import os
import re
import json
import logging
from typing import Dict, List
from groq import AsyncGroq

logger = logging.getLogger(__name__)

class RiskAnalyzer:
    """
    Active LLM-based Triage Agent for Mind-Mate.
    Wraps the Groq API to return a strictly parsed JSON response
    containing the bot's conversational reply and the assessed risk tier.
    """

    def __init__(self) -> None:
        # Require GROQ_API_KEY environment variable
        self.client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
        
        # We use a fast, reliable model for real-time WebSocket chat
        self.model = "llama3-8b-8192"

        # Strict JSON-enforcing System Prompt
        self.system_prompt = """You are Mind-Mate, an empathetic digital mental health triage assistant.
Your task is to converse with the student and assess their current mental state.

You MUST output ONLY a valid, parseable JSON object with exactly two keys:
1. "bot_reply": (string) Your active, empathetic, and supportive response to the user.
2. "risk_tier": (integer) Categorized as follows:
   - 1 (Normal): General conversation, mild stress, or typical student struggles.
   - 2 (Counselor needed): Noticeable distress, severe anxiety, depressive signs, hopelessness.
   - 3 (Immediate SOS): Mentions of self-harm, suicide, or immediate physical danger.

Do not include markdown blocks, pleasantries, or preamble. Return ONLY the raw JSON object."""

        # Retained legacy regex patterns for emergency local fallback
        self.patterns = {
            "hopelessness": [
                r"\bno hope\b", r"\bhopeless\b", r"\bwhat(?:'|’)s the point\b",
                r"\bnothing will get better\b", r"\bnever get better\b", r"\bno future\b",
            ],
            "severe_distress": [
                r"\bi can(?:'|’)t take this\b", r"\bi can(?:'|’)t do this anymore\b",
                r"\bfalling apart\b", r"\bcompletely broken\b", r"\bcan(?:'|’)t handle this\b",
                r"\bextremely overwhelmed\b",
            ],
            "social_withdrawal": [
                r"\bwant to be alone\b", r"\bstay away from everyone\b",
                r"\bdon(?:'|’)t want to talk\b", r"\bno one understands\b",
                r"\bfeel isolated\b", r"\bfeel alone\b",
            ],
            "negative_self_view": [
                r"\bfeel useless\b", r"\bfeel worthless\b", r"\bhate myself\b",
                r"\bi am a failure\b", r"\bi(?:'|’)m a failure\b", r"\bworthless\b", r"\buseless\b",
            ],
            "sleep_energy_concern": [
                r"\bcan(?:'|’)t sleep\b", r"\bsleeping all day\b", r"\bno energy\b",
                r"\balways tired\b", r"\bcompletely exhausted\b", r"\bexhausted\b",
            ],
            "self_harm_language": [
                r"\bhurt myself\b", r"\bharm myself\b", r"\bcut myself\b",
                r"\bend my life\b", r"\bkill myself\b", r"\bsuicide\b",
                r"\bdon(?:'|’)t want to live\b", r"\bdo not want to live\b",
                r"\bi do not want to live\b", r"\bwant to die\b",
            ],
        }

    def _fallback_safety_check(self, text: str) -> int:
        """
        Runs the legacy regex dictionary over the text to determine
        if the API failure is masking an immediate SOS situation.
        """
        text = text.lower()
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    if category == "self_harm_language":
                        return 3
        # If API fails but no SOS is detected locally, default to Tier 2
        return 2

    async def generate_triage_response(self, chat_history: List[Dict[str, str]], latest_scrubbed_message: str) -> dict:
        """
        Asynchronously calls the Groq API to generate a triage response.
        Enforces a JSON return format: {"bot_reply": "...", "risk_tier": 1|2|3}
        """
        # Construct messages payload
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(chat_history)
        messages.append({"role": "user", "content": latest_scrubbed_message})

        try:
            # Call Groq API with forced JSON response format
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3, # Low temp for more deterministic tiering
                response_format={"type": "json_object"}
            )
            
            raw_response = completion.choices[0].message.content
            parsed_data = json.loads(raw_response)
            
            # Validate output types to prevent downstream crashes in the WebSockets
            bot_reply = str(parsed_data.get("bot_reply", "I'm here to listen. Tell me more."))
            risk_tier = int(parsed_data.get("risk_tier", 2))
            
            if risk_tier not in [1, 2, 3]:
                risk_tier = 2
                
            return {
                "bot_reply": bot_reply,
                "risk_tier": risk_tier
            }

        except Exception as e:
            logger.error(f"Groq API Error or JSON Parsing failure: {e}")
            
            # Immediate safety fallback if Groq API fails
            emergency_tier = self._fallback_safety_check(latest_scrubbed_message)
            
            return {
                "bot_reply": "I'm having a little trouble connecting. Please hold on.",
                "risk_tier": emergency_tier
            }