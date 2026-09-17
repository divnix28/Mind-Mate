from backend_api.database import SessionLocal, engine, Base
from backend_api.models import FlaggedEntry, ReviewStatus

def seed_database():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Check if data already exists
    if db.query(FlaggedEntry).count() > 0:
        print("Database is already seeded!")
        db.close()
        return

    # Mock anonymized data
    mock_entries = [
        FlaggedEntry(sanitized_text="I just feel like giving up entirely.", risk_score=0.85, status=ReviewStatus.PENDING_REVIEW),
        FlaggedEntry(sanitized_text="The stress from [REDACTED] is too much.", risk_score=0.65, status=ReviewStatus.PENDING_REVIEW),
        FlaggedEntry(sanitized_text="I have a plan to end it tonight.", risk_score=0.99, status=ReviewStatus.PENDING_REVIEW)
    ]

    db.add_all(mock_entries)
    db.commit()
    print(f"Successfully seeded database with {len(mock_entries)} mock entries.")
    db.close()

if __name__ == "__main__":
    seed_database()