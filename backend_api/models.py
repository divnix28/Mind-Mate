from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from .database import Base

class SessionStatus(str, enum.Enum):
    LIVE_BOT = "LIVE_BOT"
    AWAITING_COUNSELOR = "AWAITING_COUNSELOR"
    LIVE_COUNSELOR = "LIVE_COUNSELOR"
    CRITICAL_SOS = "CRITICAL_SOS"

class SenderType(str, enum.Enum):
    STUDENT = "STUDENT"
    BOT = "BOT"
    COUNSELOR = "COUNSELOR"

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    reg_no = Column(String, unique=True, index=True, nullable=False)
    block = Column(String)
    room = Column(String)
    phone = Column(String)
    password_hash = Column(String, nullable=False)

class Counselor(Base):
    __tablename__ = "counselors"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    status = Column(Enum(SessionStatus), default=SessionStatus.LIVE_BOT)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    student = relationship("Student")
    messages = relationship("Message", back_populates="session")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    sender_type = Column(Enum(SenderType), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("ChatSession", back_populates="messages")