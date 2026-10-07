from backend_api.database import SessionLocal, engine, Base
from backend_api.models import Student, ChatSession, SessionStatus

def seed_database():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Check if a student already exists
    student = db.query(Student).first()
    if not student:
        student = Student(
            name="Alex",
            reg_no="21BCE1001",
            block="BH-3",
            room="405",
            phone="+91-9876543210",
            password_hash="demo_student_hash"
        )
        db.add(student)
        db.commit()
        db.refresh(student)
        print(f"Created demo student: {student.name} ({student.reg_no})")

    # Check if chat session already exists
    session = db.query(ChatSession).filter(ChatSession.student_id == student.id).first()
    if not session:
        session = ChatSession(
            student_id=student.id,
            status=SessionStatus.LIVE_BOT
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        print(f"Created demo ChatSession #{session.id} (Status: {session.status})")
    else:
        print(f"ChatSession #{session.id} already exists (Status: {session.status})")

    print(f"Database ready! You can test with Session ID: {session.id}")
    db.close()

if __name__ == "__main__":
    seed_database()