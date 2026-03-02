from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime, timezone
from app.db.base import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=False)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True)
    profile_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
