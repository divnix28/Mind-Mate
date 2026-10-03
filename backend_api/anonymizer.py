import re
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

class PIIAnonymizer:
    def __init__(self):
        self.analyzer = AnalyzerEngine(supported_languages=["en"])
        self.anonymizer = AnonymizerEngine()
        self._add_custom_recognizers()

    def _add_custom_recognizers(self):
        # 1. Existing: Student ID
        student_id_pattern = Pattern(
            name="student_id_regex",
            regex=r"\b\d{2}[A-Z]{3}\d{4}\b",
            score=0.95
        )
        self.analyzer.registry.add_recognizer(
            PatternRecognizer(supported_entity="STUDENT_ID", patterns=[student_id_pattern])
        )

        # 2. Existing: Social Handle
        social_pattern = Pattern(
            name="social_handle_regex",
            regex=r"(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z0-9_]+)",
            score=0.85
        )
        self.analyzer.registry.add_recognizer(
            PatternRecognizer(supported_entity="SOCIAL_HANDLE", patterns=[social_pattern])
        )

        # 3. New: Hostel Block Recognizer
        hostel_block_pattern = Pattern(
            name="hostel_block_regex",
            regex=r"(?i)\b(?:block\s+[a-z0-9]+|hostel\s+\d+|[a-z]{2,3}-\d+|boys hostel|girls hostel)\b",
            score=0.65
        )
        self.analyzer.registry.add_recognizer(
            PatternRecognizer(
                supported_entity="HOSTEL_BLOCK", 
                patterns=[hostel_block_pattern],
                context=["hostel", "block", "campus", "staying", "living", "floor"]
            )
        )

        # 4. New: Room Number Recognizer
        # Explicit catches "Room 405", Implicit catches "D-104" (relies on context words to boost score)
        room_pattern_explicit = Pattern(
            name="room_number_explicit",
            regex=r"(?i)\broom\s+[a-z]?[-\s]?\d{1,4}\b",
            score=0.85
        )
        room_pattern_implicit = Pattern(
            name="room_number_implicit",
            regex=r"\b[A-Za-z]-\d{2,4}\b",
            score=0.40 
        )
        self.analyzer.registry.add_recognizer(
            PatternRecognizer(
                supported_entity="ROOM_NUMBER",
                patterns=[room_pattern_explicit, room_pattern_implicit],
                context=["room", "floor", "hostel", "block", "bh", "gh"]
            )
        )

        # 5. New: Indian Phone Number Enhancer
        # Catches standard 10-digit formats starting with 6-9, with or without +91/091
        in_phone_pattern = Pattern(
            name="in_phone_regex",
            regex=r"(?:(?:\+|00)91[-\s]?)?(?:\b[6-9]\d{9}\b|\b[6-9]\d{4}[-\s]\d{5}\b)",
            score=0.85
        )
        self.analyzer.registry.add_recognizer(
            PatternRecognizer(
                supported_entity="PHONE_NUMBER", # Augmenting Presidio's default phone entity
                patterns=[in_phone_pattern],
                context=["phone", "call", "mobile", "number", "whatsapp"]
            )
        )

    def clean_text(self, text: str) -> str:
        if not text:
            return text

        # Added new campus-specific entities
        entities = [
            "PERSON", "LOCATION", "PHONE_NUMBER", "EMAIL_ADDRESS", 
            "STUDENT_ID", "SOCIAL_HANDLE", "HOSTEL_BLOCK", "ROOM_NUMBER"
        ]

        results = self.analyzer.analyze(
            text=text,
            entities=entities,
            language="en",
            score_threshold=0.5
        )

        operators = {
            entity: OperatorConfig("replace", {"new_value": f"[{entity}]"}) 
            for entity in entities
        }

        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators
        )

        return anonymized_result.text