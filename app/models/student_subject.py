from sqlalchemy import Column, BigInteger, DateTime, ForeignKey, PrimaryKeyConstraint
from datetime import datetime, timezone
from app.db.base import Base


class StudentSubject(Base):
    __tablename__ = "student_subjects"

    student_id = Column(BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    selected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        PrimaryKeyConstraint("student_id", "subject_id"),
    )
