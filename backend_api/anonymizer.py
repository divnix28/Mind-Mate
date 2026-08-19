from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine

class PIIAnonymizer:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()

        # Custom pattern for University Roll Numbers / Student IDs (e.g., 21BCE1001)
        student_id_pattern = Pattern(
            name="student_id_pattern",
            regex=r"\b\d{2}[A-Z]{3}\d{4}\b",
            score=0.90
        )
        student_id_recognizer = PatternRecognizer(
            supported_entity="STUDENT_ID",
            patterns=[student_id_pattern]
        )
        self.analyzer.registry.add_recognizer(student_id_recognizer)

    def clean_text(self, text: str) -> str:
        # Analyze text for PII entities
        results = self.analyzer.analyze(
            text=text,
            entities=["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "LOCATION", "STUDENT_ID"],
            language="en"
        )

        # Redact detected entities
        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results
        )

        return anonymized_result.text

if __name__ == "__main__":
    # Local test execution
    scrubber = PIIAnonymizer()
    sample = "Hi, I am Alex Smith (ID: 21BCE1001). Contact me at alex@example.com or 9876543210 in Bhopal."
    print("\n--- Original Text ---")
    print(sample)
    print("\n--- Scrubbed Text ---")
    print(scrubber.clean_text(sample))