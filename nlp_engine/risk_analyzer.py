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
        
        # Use active Groq models (llama3-8b-8192 was decommissioned by Groq)
        self.model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
        self.candidate_models = [
            self.model,
            "openai/gpt-oss-120b",
            "qwen/qwen3.8-27b",
        ]

        # Strict JSON-enforcing System Prompt
        self.system_prompt = """You are Mind-Mate, an empathetic digital mental health triage assistant.
Your task is to converse with the student and assess their current mental state based on their latest message in context.

IMPORTANT PRIVACY DIRECTIVE: NEVER repeat or mirror back any student personal identifiers (such as names, registration numbers, hostel rooms, or phone numbers) in your replies. Always address the student neutrally and warmly without stating their personal name or registration number.

You MUST output ONLY a valid, parseable JSON object with exactly two keys:
1. "bot_reply": (string) Your active, empathetic, and supportive response to the user.
2. "risk_tier": (integer) Categorized as follows:
   - 1 (Normal): General conversation, mild stress, typical student struggles, or student currently feeling better/stable.
   - 2 (Counselor needed): Active noticeable distress, severe anxiety, depressive signs, hopelessness, OR if the student is actively asking to speak to/connect with a counselor or human.
   - 3 (Immediate SOS): Mentions of self-harm, suicide, or immediate physical danger.

CRITICAL: Assess the student's LATEST message. If the student is expressing relief, gratitude, or having normal conversation, set risk_tier to 1. Only set risk_tier to 2 if the student is actively in distress or actively asking for human assistance.
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
                r"\bend\s+(?:my\s*)?life\b", r"\bkill\s+(?:my\s*)?s[le]{2,4}f\b", r"\bsuicid[a-z]*\b",
                r"\bdon(?:'|’)t\s+want\s+to\s+live\b", r"\bdo not want to live\b",
                r"\bi do not want to live\b", r"\bwant to die\b", r"\bkill\s+me\b",
                r"\bhang\s+(?:my\s*)?s[le]{2,4}f\b", r"\bbetter\s+off\s+dead\b",
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
        # CRITICAL LIFE-SAFETY OVERRIDE:
        # Detect explicit self-harm or suicidal intent deterministically (including typos like 'my slef', 'myslef')
        suicide_patterns = [
            r"\bkill\s+(?:my\s*)?s[le]{2,4}f\b",
            r"\bkill\s+me\b",
            r"\bend\s+(?:my\s*)?life\b",
            r"\bsuicid[a-z]*\b",
            r"\bwant\s+to\s+die\b",
            r"\bwish\s+i\s+(?:was|were)\s+dead\b",
            r"\bhang\s+(?:my\s*)?s[le]{2,4}f\b",
            r"\btake\s+my\s+(?:own\s+)?life\b",
            r"\bslit\s+(?:my\s*)?wrist[s]?\b",
            r"\boverdose\b",
            r"\bjump\s+off\b",
            r"\bdon(?:'|’)?t\s+want\s+to\s+live\b",
            r"\bno\s+reason\s+to\s+live\b",
            r"\bbetter\s+off\s+dead\b",
            r"\bi(?:\s*will|'ll|\s*m\s+gonna)\s+kill\s+(?:my\s*)?s[le]{2,4}f\b"
        ]
        for pat in suicide_patterns:
            if re.search(pat, latest_scrubbed_message, re.IGNORECASE):
                logger.warning(f"Immediate Critical SOS Triggered for: {latest_scrubbed_message}")
                return {
                    "bot_reply": "I hear how much pain you are carrying right now. Please know that your life matters and you are not alone. I am immediately alerting our campus emergency support team and connecting a counselor to stay with you.",
                    "risk_tier": 3
                }

        # Construct messages payload
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(chat_history)
        messages.append({"role": "user", "content": latest_scrubbed_message})

        last_error = None
        for model_name in self.candidate_models:
            try:
                # Call Groq API with forced JSON response format
                completion = await self.client.chat.completions.create(
                    model=model_name,
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

                # If student explicitly asks for counselor or human, enforce Tier 2 escalation
                if re.search(r"\b(counselor|counsellor|human|therapist|doctor|talk to someone|speak to someone)\b", latest_scrubbed_message, re.IGNORECASE):
                    risk_tier = max(risk_tier, 2)
                    
                return {
                    "bot_reply": bot_reply,
                    "risk_tier": risk_tier
                }

            except Exception as e:
                last_error = e
                logger.warning(f"Groq model {model_name} failed: {e}. Trying next candidate...")

        logger.error(f"All Groq models failed. Last error: {last_error}")
        
        # Immediate safety fallback if all Groq models fail
        emergency_tier = self._fallback_safety_check(latest_scrubbed_message)
        
        return {
            "bot_reply": "I'm having a little trouble connecting. Please hold on.",
            "risk_tier": emergency_tier
        }