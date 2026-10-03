from backend_api.anonymizer import PIIAnonymizer

def test_pipeline():
    print("Initializing Presidio Analyzer & NLP Engine...")
    anonymizer = PIIAnonymizer()
    
    test_string = "I'm Alex from BH-3 Room 405. Call my mom at +91-9876543210. My ID is 21BCE1001."
    
    print("\n=== Mind-Mate Tier 1 Firewall Validation ===")
    print(f"ORIGINAL TEXT : {test_string}")
    
    scrubbed_string = anonymizer.clean_text(test_string)
    
    print(f"SCRUBBED TEXT : {scrubbed_string}")

if __name__ == "__main__":
    test_pipeline()