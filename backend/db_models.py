from datetime import datetime

from database import Base
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True)

    profiles = relationship("BehaviorProfile", back_populates="student")
    sessions = relationship("ExamSession", back_populates="student")


class BehaviorProfile(Base):
    __tablename__ = "behavior_profiles"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    avg_dwell_time = Column(Float)
    avg_flight_time = Column(Float)
    typing_speed = Column(Float)
    mouse_velocity = Column(Float)
    sample_count = Column(Integer, default=0)
    enrollment_status = Column(String, default="ENROLLING")
    enrollment_count = Column(Integer, default=0)

    student = relationship("Student", back_populates="profiles")



class EnrollmentBuffer(Base):
    __tablename__ = "enrollment_buffers"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    avg_dwell_time = Column(Float, nullable=False)
    avg_flight_time = Column(Float, nullable=False)
    typing_speed = Column(Float, nullable=False)
    mouse_velocity = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ExamSession(Base):
    __tablename__ = "exam_sessions"


    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)

    student = relationship("Student", back_populates="sessions")
    trust_logs = relationship("TrustLog", back_populates="session")


class TrustLog(Base):
    __tablename__ = "trust_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("exam_sessions.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    trust_score = Column(Float)
    decision_score = Column(Float)
    avg_dwell = Column(Float)
    avg_flight = Column(Float)
    typing_speed = Column(Float)
    avg_mouse_velocity = Column(Float)

    session = relationship("ExamSession", back_populates="trust_logs")


class AuditLog(Base):
    """
    Cryptographically verifiable tamper-evident security audit log with SHA-256 hash chaining.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    target = Column(String, nullable=False)
    result = Column(String, nullable=False)
    details = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    previous_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False)