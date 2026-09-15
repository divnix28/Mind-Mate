"""
Mind-Mate NLP Risk Analysis Engine

IMPORTANT:
This is a NON-DIAGNOSTIC screening system.

It identifies linguistic indicators that may warrant human review.
It must NOT be used to diagnose a mental-health condition or determine
clinical treatment.
"""

import re
from typing import Dict, List


class RiskAnalyzer:
    """
    Explainable, non-diagnostic NLP risk screening engine.

    The analyzer combines:
        1. Linguistic pattern detection
        2. Weighted risk scoring
        3. Human-in-the-loop escalation

    Input:
        anonymized_text: Text after PII anonymization.

    Output:
        {
            "risk_score": float,
            "risk_level": "LOW" | "MEDIUM" | "HIGH",
            "linguistic_flags": list,
            "requires_hitl": bool
        }
    """

    def __init__(self) -> None:

        # Patterns are indicators for screening only.
        # They are NOT clinical diagnostic criteria.
        self.patterns = {

            "hopelessness": [
                r"\bno hope\b",
                r"\bhopeless\b",
                r"\bwhat(?:'|’)s the point\b",
                r"\bnothing will get better\b",
                r"\bnever get better\b",
                r"\bno future\b",
            ],

            "severe_distress": [
                r"\bi can(?:'|’)t take this\b",
                r"\bi can(?:'|’)t do this anymore\b",
                r"\bfalling apart\b",
                r"\bcompletely broken\b",
                r"\bcan(?:'|’)t handle this\b",
                r"\bextremely overwhelmed\b",
            ],

            "social_withdrawal": [
                r"\bwant to be alone\b",
                r"\bstay away from everyone\b",
                r"\bdon(?:'|’)t want to talk\b",
                r"\bno one understands\b",
                r"\bfeel isolated\b",
                r"\bfeel alone\b",
            ],

            "negative_self_view": [
                r"\bfeel useless\b",
                r"\bfeel worthless\b",
                r"\bhate myself\b",
                r"\bi am a failure\b",
                r"\bi(?:'|’)m a failure\b",
                r"\bworthless\b",
                r"\buseless\b",
            ],

            "sleep_energy_concern": [
                r"\bcan(?:'|’)t sleep\b",
                r"\bsleeping all day\b",
                r"\bno energy\b",
                r"\balways tired\b",
                r"\bcompletely exhausted\b",
                r"\bexhausted\b",
            ],

            "self_harm_language": [
   		 r"\bhurt myself\b",
		 r"\bharm myself\b",
 		 r"\bcut myself\b",
 		 r"\bend my life\b",
    		 r"\bkill myself\b",
    		 r"\bsuicide\b",
    		 r"\bdon(?:'|’)t want to live\b",
    		 r"\bdo not want to live\b",
    		 r"\bi do not want to live\b",
    		 r"\bwant to die\b",
	    ],
        }

        # Explainable weights.
        self.weights = {

            "hopelessness": 0.25,
            "severe_distress": 0.20,
            "social_withdrawal": 0.10,
            "negative_self_view": 0.20,
            "sleep_energy_concern": 0.10,

            # Deliberately high because this should trigger HITL.
            "self_harm_language": 0.70,
        }

    # ---------------------------------------------------------
    # Text preprocessing
    # ---------------------------------------------------------

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normalize text before pattern detection.
        """

        text = text.strip()

        # Normalize curly apostrophes.
        text = text.replace("’", "'")

        # Collapse repeated whitespace.
        text = re.sub(r"\s+", " ", text)

        return text.lower()

    # ---------------------------------------------------------
    # Linguistic pattern detection
    # ---------------------------------------------------------

    def _detect_patterns(self, text: str) -> List[str]:
        """
        Detect predefined linguistic indicators.

        Returns:
            List of detected categories.
        """

        flags = []

        for category, patterns in self.patterns.items():

            for pattern in patterns:

                if re.search(
                    pattern,
                    text,
                    flags=re.IGNORECASE
                ):
                    flags.append(category)
                    break

        return flags

    # ---------------------------------------------------------
    # Negation handling
    # ---------------------------------------------------------

    @staticmethod
    def _remove_negated_matches(text: str, flags: List[str]) -> List[str]:
        """
        Remove some obvious false-positive cases.

        Example:
            "I am not hopeless"

        should not automatically trigger hopelessness.

        This is intentionally conservative rather than attempting
        to perform full linguistic parsing.
        """

        negation_patterns = {

            "hopelessness": [
                r"\bnot hopeless\b",
                r"\bnever hopeless\b",
            ],

            "negative_self_view": [
                r"\bnot worthless\b",
                r"\bnot useless\b",
                r"\bnot a failure\b",
            ],

            "social_withdrawal": [
                r"\bnot alone\b",
            ],
        }

        filtered_flags = []

        for flag in flags:

            negated = False

            for pattern in negation_patterns.get(flag, []):

                if re.search(
                    pattern,
                    text,
                    flags=re.IGNORECASE
                ):
                    negated = True
                    break

            if not negated:
                filtered_flags.append(flag)

        return filtered_flags

    # ---------------------------------------------------------
    # Risk score
    # ---------------------------------------------------------

    def _calculate_score(self, flags: List[str]) -> float:
        """
        Calculate explainable weighted risk score.
        """

        score = sum(
            self.weights.get(flag, 0.0)
            for flag in flags
        )

        return min(score, 1.0)

    # ---------------------------------------------------------
    # Risk level
    # ---------------------------------------------------------

    @staticmethod
    def _get_risk_level(
        score: float,
        flags: List[str]
    ) -> str:
        """
        Convert screening score to risk level.

        Self-harm language receives HIGH priority so that
        human review is not dependent only on the numeric score.
        """

        if "self_harm_language" in flags:
            return "HIGH"

        if score >= 0.60:
            return "HIGH"

        if score >= 0.30:
            return "MEDIUM"

        return "LOW"

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def analyze_entry(
        self,
        anonymized_text: str
    ) -> Dict:
        """
        Analyze an anonymized student entry.

        Args:
            anonymized_text:
                PII-scrubbed text.

        Returns:
            Dictionary containing:

                risk_score:
                    Float from 0.0 to 1.0.

                risk_level:
                    LOW / MEDIUM / HIGH.

                linguistic_flags:
                    Detected linguistic indicator categories.

                requires_hitl:
                    True when human review is required.
        """

        # Empty input.
        if not anonymized_text or not anonymized_text.strip():

            return {
                "risk_score": 0.0,
                "risk_level": "LOW",
                "linguistic_flags": [],
                "requires_hitl": False,
            }

        # Normalize.
        text = self._normalize_text(
            anonymized_text
        )

        # Detect linguistic indicators.
        flags = self._detect_patterns(text)

        # Remove obvious negation false positives.
        flags = self._remove_negated_matches(
            text,
            flags
        )

        # Calculate score.
        score = self._calculate_score(flags)

        # Determine screening level.
        risk_level = self._get_risk_level(
            score,
            flags
        )

        # Human review policy.
        requires_hitl = risk_level == "HIGH"

        return {
            "risk_score": round(score, 3),
            "risk_level": risk_level,
            "linguistic_flags": flags,
            "requires_hitl": requires_hitl,
        }