import sqlite3
import hashlib
from .database import engine, Base, SessionLocal
from .models import Student, Counselor

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def ensure_schema_and_seed():
    Base.metadata.create_all(bind=engine)

    # Raw sqlite check for column additions if table was already created
    db_file = None
    if "sqlite:///" in str(engine.url):
        db_path = str(engine.url).replace("sqlite:///", "")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check students.email
            cursor.execute("PRAGMA table_info(students);")
            student_cols = [row[1] for row in cursor.fetchall()]
            if "email" not in student_cols:
                cursor.execute("ALTER TABLE students ADD COLUMN email VARCHAR;")
            
            # Check counselors.name
            cursor.execute("PRAGMA table_info(counselors);")
            counselor_cols = [row[1] for row in cursor.fetchall()]
            if "name" not in counselor_cols:
                cursor.execute("ALTER TABLE counselors ADD COLUMN name VARCHAR;")

            # Check chat_sessions.counselor_id
            cursor.execute("PRAGMA table_info(chat_sessions);")
            session_cols = [row[1] for row in cursor.fetchall()]
            if "counselor_id" not in session_cols:
                cursor.execute("ALTER TABLE chat_sessions ADD COLUMN counselor_id INTEGER;")
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Seed] Schema alter check note: {e}")

    db = SessionLocal()
    try:
        # 1. Seed Demo Students
        demo_students = [
            {
                "name": "Divyanshu",
                "reg_no": "21BCE1001",
                "email": "divyanshu@campus.edu",
                "phone": "+91-9876543211",
                "block": "BH-1",
                "room": "101",
                "password": "password123"
            },
            {
                "name": "Varun",
                "reg_no": "21BCE1002",
                "email": "varun@campus.edu",
                "phone": "+91-9876543212",
                "block": "BH-2",
                "room": "202",
                "password": "password123"
            },
            {
                "name": "Vedant",
                "reg_no": "21BCE1003",
                "email": "vedant@campus.edu",
                "phone": "+91-9876543213",
                "block": "BH-3",
                "room": "303",
                "password": "password123"
            },
            {
                "name": "Siddhesh",
                "reg_no": "21BCE1004",
                "email": "siddhesh@campus.edu",
                "phone": "+91-9876543214",
                "block": "BH-1",
                "room": "104",
                "password": "password123"
            },
            {
                "name": "Vihan",
                "reg_no": "21BCE1005",
                "email": "vihan@campus.edu",
                "phone": "+91-9876543215",
                "block": "BH-2",
                "room": "205",
                "password": "password123"
            }
        ]

        for s_data in demo_students:
            existing = db.query(Student).filter(
                (Student.email == s_data["email"]) | (Student.reg_no == s_data["reg_no"])
            ).first()
            if not existing:
                student = Student(
                    name=s_data["name"],
                    reg_no=s_data["reg_no"],
                    email=s_data["email"],
                    phone=s_data["phone"],
                    block=s_data["block"],
                    room=s_data["room"],
                    password_hash=hash_password(s_data["password"])
                )
                db.add(student)
            else:
                # Update details to match requested dummy profile
                existing.name = s_data["name"]
                existing.email = s_data["email"]
                existing.phone = s_data["phone"]
                existing.block = s_data["block"]
                existing.room = s_data["room"]
                existing.password_hash = hash_password(s_data["password"])

        # 2. Seed Demo Counselors
        demo_counselors = [
            {
                "employee_id": "counselor_vkt",
                "name": "Dr. Vijay Kumar Trivedi",
                "password": "counselor123"
            },
            {
                "employee_id": "counselor_kps",
                "name": "Dr. Kunwar Pratap Singh",
                "password": "counselor123"
            }
        ]

        for c_data in demo_counselors:
            existing_c = db.query(Counselor).filter(Counselor.employee_id == c_data["employee_id"]).first()
            if not existing_c:
                counselor = Counselor(
                    employee_id=c_data["employee_id"],
                    name=c_data["name"],
                    password_hash=hash_password(c_data["password"])
                )
                db.add(counselor)
            else:
                existing_c.name = c_data["name"]
                existing_c.password_hash = hash_password(c_data["password"])

        db.commit()
        print("[Seed] Successfully verified and seeded students and counselors.")
    except Exception as e:
        db.rollback()
        print(f"[Seed] Error seeding users: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    ensure_schema_and_seed()
