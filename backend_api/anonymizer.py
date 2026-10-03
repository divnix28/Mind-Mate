import re
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

class PIIAnonymizer:
    def __init__(self):
        # Explicitly configure Presidio to use the lightweight small model
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }
        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()

        self.analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine,
            supported_languages=["en"]
        )
        self.anonymizer = AnonymizerEngine()
        self._add_custom_recognizers()

    def _add_custom_recognizers(self):
        student_id_pattern = Pattern(
            name="student_id_regex",
            regex=r"\b\d{2}[A-Z]{3}\d{4}\b",
            score=0.95
        )
        self.analyzer.registry.add_recognizer(
            PatternRecognizer(supported_entity="STUDENT_ID", patterns=[student_id_pattern])
        )

        social_pattern = Pattern(
            name="social_handle_regex",
            regex=r"(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z0-9_]+)",
            score=0.85
        )
        self.analyzer.registry.add_recognizer(
            PatternRecognizer(supported_entity="SOCIAL_HANDLE", patterns=[social_pattern])
        )

    def clean_text(self, text: str) -> str:
        if not text:
            return text

        entities = [
            "PERSON", "LOCATION", "PHONE_NUMBER", "EMAIL_ADDRESS", 
            "STUDENT_ID", "SOCIAL_HANDLE"
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