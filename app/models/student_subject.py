from sqlalchemy import Column, BigInteger, Integer, DateTime, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base


class StudentSubject(Base):
    __tablename__ = "student_subjects"

    student_id = Column(BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    selected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    subject = relationship("Subject", lazy="joined")

    __table_args__ = (
        PrimaryKeyConstraint("student_id", "subject_id"),
    )
