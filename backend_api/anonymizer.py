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
        # 1. Enhanced Student ID / Registration Number Recognizer
        # Matches alphanumeric college formats (e.g. 24BCE13121, 21BCE1001, 2024BCSE089)
        student_id_alphanumeric = Pattern(
            name="student_id_alphanumeric",
            regex=r"\b\d{2,4}[A-Za-z]{2,5}\d{3,6}\b",
            score=0.95
        )
        # Numeric roll numbers (e.g. 10001010, 101010101)
        student_id_numeric = Pattern(
            name="student_id_numeric",
            regex=r"\b\d{8,10}\b",
            score=0.75
        )
        self.analyzer.registry.add_recognizer(
            PatternRecognizer(
                supported_entity="STUDENT_ID",
                patterns=[student_id_alphanumeric, student_id_numeric],
                context=["registration", "reg", "roll", "student", "admit", "card", "enrollment", "number", "id"]
            )
        )

        # 1b. Common Indian & International Names Dictionary (Expanded)
        indian_names = [
            "Aarav", "Aanya", "Aarush", "Aayush", "Abhay", "Abhinav", "Abhishek", "Aditi", "Aditya",
            "Advait", "Akash", "Akshay", "Amit", "Amrita", "Ananya", "Aniket", "Anil", "Anish", "Anjali",
            "Ankit", "Ankush", "Anmol", "Ansh", "Anushka", "Arjun", "Arman", "Arnav", "Aryan",
            "Ashish", "Ashok", "Atharv", "Avani", "Ayaan", "Ayush", "Bhavya", "Chetan", "Chirag", "Deepa",
            "Deepak", "Dev", "Devansh", "Dhruv", "Divya", "Divyanshu", "Gaurav", "Gautam", "Gayatri", "Geeta",
            "Harish", "Harsh", "Hemant", "Himanshu", "Isha", "Ishaan", "Jay", "Kabir", "Kajal", "Kamal",
            "Kapil", "Karan", "Kavya", "Keshav", "Khushi", "Kiran", "Komal", "Krishna", "Kunal",
            "Lakshya", "Madhav", "Manish", "Manoj", "Mayank", "Meera", "Mohan", "Mohit", "Mukesh",
            "Naveen", "Navya", "Neha", "Nidhi", "Nikhil", "Nilesh", "Nisha", "Nitin", "Om",
            "Pankaj", "Parth", "Payal", "Pooja", "Poonam", "Pradeep", "Prakash", "Pranav", "Prashant",
            "Prateek", "Praveen", "Prem", "Priya", "Priyanka", "Rahul", "Raj", "Rajat", "Rajeev",
            "Rajesh", "Rakesh", "Ramesh", "Ravi", "Reyansh", "Rishabh", "Rishi", "Riya", "Rohan", "Rohit",
            "Rudra", "Rupesh", "Sachin", "Sahil", "Samarth", "Sameer", "Sandeep", "Sanjay", "Sanjeev", "Sarthak", "Sarvesh",
            "Satish", "Saurabh", "Shaurya", "Shashank", "Shivam", "Shivani", "Shreya", "Shubham", "Siddhesh",
            "Siddharth", "Simran", "Sneha", "Sonia", "Sourabh", "Subhash", "Suhas", "Sujit", "Suman",
            "Sumit", "Sunil", "Suraj", "Suresh", "Surya", "Swapnil", "Swati", "Tanmay", "Tanvi",
            "Tarun", "Tejas", "Tushar", "Umesh", "Utkarsh", "Vaibhav", "Varun", "Vicky", "Vidya",
            "Vihan", "Vihaan", "Vijay", "Vikas", "Vinay", "Vinod", "Vipul", "Vishal", "Vivek", "Yash", "Yuvraj",
            "vihan", "vihaan", "varun", "rahul", "rohan", "priya", "aarav", "divyanshu", "siddhesh", "amit", "alex", "david"
        ]
        self.analyzer.registry.add_recognizer(
            PatternRecognizer(supported_entity="PERSON", deny_list=indian_names)
        )

        # 1c. Name Introduction Context Recognizer (Catches any name after "my name is", "i am", "call me", etc.)
        name_intro_pattern = Pattern(
            name="name_intro_lookbehind",
            regex=r"(?i)(?<=\bmy name is\s)[a-zA-Z]{2,25}\b|(?<=\bi am\s)[a-zA-Z]{2,25}\b|(?<=\bi\'m\s)[a-zA-Z]{2,25}\b|(?<=\bthis is\s)[a-zA-Z]{2,25}\b|(?<=\bcall me\s)[a-zA-Z]{2,25}\b|(?<=\bmyself\s)[a-zA-Z]{2,25}\b|(?<=\bname is\s)[a-zA-Z]{2,25}\b",
            score=0.95
        )
        self.analyzer.registry.add_recognizer(
            PatternRecognizer(supported_entity="PERSON", patterns=[name_intro_pattern])
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