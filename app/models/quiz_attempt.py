from sqlalchemy import Column, Integer, BigInteger, Numeric, DateTime, ForeignKey, CheckConstraint
from datetime import datetime, timezone
from app.db.base import Base


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_session_id = Column(Integer, ForeignKey("quiz_sessions.id", ondelete="CASCADE"), unique=True, nullable=False)
    student_id = Column(BigInteger, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    score_percentage = Column(Numeric(5, 2), nullable=True)
    total_correct = Column(Integer, nullable=True)
    total_questions = Column(Integer, nullable=True)
    xp_earned = Column(Integer, nullable=True)
    completed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("score_percentage BETWEEN 0 AND 100"),
        CheckConstraint("total_correct >= 0"),
        CheckConstraint("total_questions >= 0"),
        CheckConstraint("xp_earned >= 0"),
    )
