from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import hashlib
from typing import Optional
from .database import get_db
from .models import Student, Counselor

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & Profiles"])

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# Schemas
class StudentRegisterRequest(BaseModel):
    name: str
    reg_no: str
    email: str
    phone: str
    block: str
    room: str
    password: str

class StudentLoginRequest(BaseModel):
    email: str
    password: str

class CounselorLoginRequest(BaseModel):
    employee_id: str
    password: str

# 1. Student Registration
@router.post("/student/register")
def register_student(req: StudentRegisterRequest, db: Session = Depends(get_db)):
    # Check if reg_no or email already registered
    existing_reg = db.query(Student).filter(Student.reg_no == req.reg_no.strip()).first()
    if existing_reg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration Number '{req.reg_no}' is already registered."
        )

    existing_email = db.query(Student).filter(Student.email == req.email.strip().lower()).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{req.email}' is already registered."
        )

    new_student = Student(
        name=req.name.strip(),
        reg_no=req.reg_no.strip().upper(),
        email=req.email.strip().lower(),
        phone=req.phone.strip(),
        block=req.block.strip(),
        room=req.room.strip(),
        password_hash=hash_password(req.password)
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)

    return {
        "status": "success",
        "message": "Student account created successfully.",
        "student": {
            "id": new_student.id,
            "name": new_student.name,
            "reg_no": new_student.reg_no,
            "email": new_student.email,
            "phone": new_student.phone,
            "block": new_student.block,
            "room": new_student.room
        }
    }

# 2. Student Login (Email + Password)
@router.post("/student/login")
def login_student(req: StudentLoginRequest, db: Session = Depends(get_db)):
    email_clean = req.email.strip().lower()
    student = db.query(Student).filter(Student.email == email_clean).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if student.password_hash != hash_password(req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    return {
        "status": "success",
        "message": f"Welcome back, {student.name}!",
        "student": {
            "id": student.id,
            "name": student.name,
            "reg_no": student.reg_no,
            "email": student.email,
            "phone": student.phone,
            "block": student.block,
            "room": student.room
        }
    }

# 3. Quick Demo Students List
@router.get("/students/demo")
def get_demo_students(db: Session = Depends(get_db)):
    students = db.query(Student).limit(10).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "reg_no": s.reg_no,
            "email": s.email,
            "phone": s.phone,
            "block": s.block,
            "room": s.room
        }
        for s in students
    ]

# 4. Counselor Login (Employee ID + Password)
@router.post("/counselor/login")
def login_counselor(req: CounselorLoginRequest, db: Session = Depends(get_db)):
    emp_id_clean = req.employee_id.strip()
    counselor = db.query(Counselor).filter(Counselor.employee_id == emp_id_clean).first()
    if not counselor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Counselor ID or password."
        )

    if counselor.password_hash != hash_password(req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Counselor ID or password."
        )

    return {
        "status": "success",
        "message": f"Welcome, {counselor.name or counselor.employee_id}!",
        "counselor": {
            "id": counselor.id,
            "employee_id": counselor.employee_id,
            "name": counselor.name or counselor.employee_id
        }
    }

# 5. Quick Demo Counselors List
@router.get("/counselors/demo")
def get_demo_counselors(db: Session = Depends(get_db)):
    counselors = db.query(Counselor).all()
    return [
        {
            "id": c.id,
            "employee_id": c.employee_id,
            "name": c.name or c.employee_id
        }
        for c in counselors
    ]
