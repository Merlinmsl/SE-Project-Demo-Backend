from sqlalchemy import (
    Column, BigInteger, SmallInteger, Integer, String, Text, Boolean,
    DateTime, ForeignKey, CheckConstraint
)
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from app.db.base import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    clerk_user_id = Column(Text, unique=True, nullable=True)
    email = Column(String(255), nullable=True)
    full_name = Column(String(150), nullable=True)
    username = Column(String(50), unique=True, nullable=True)
    avatar_key = Column(String(30), nullable=True)
    grade_id = Column(SmallInteger, ForeignKey("grades.id", ondelete="SET NULL"), nullable=True)
    district_id = Column(SmallInteger, ForeignKey("districts.id", ondelete="SET NULL"), nullable=True)
    profile_completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    district = relationship("District", lazy="joined")
    grade = relationship("Grade", lazy="joined")

    __table_args__ = (
        CheckConstraint(
            """
            profile_completed = FALSE OR
            (username IS NOT NULL AND full_name IS NOT NULL AND grade_id IS NOT NULL AND district_id IS NOT NULL AND avatar_key IS NOT NULL)
            """,
            name="chk_profile_completion_required_fields",
        ),
    )
