from sqlalchemy import (
    Column, Integer, BigInteger, DateTime, ForeignKey,
    Enum as SAEnum, CheckConstraint
)
from datetime import datetime, timezone
from app.db.base import Base


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    mode = Column(SAEnum("topic", "term", name="quiz_mode_enum"), nullable=False)
    difficulty_profile = Column(
        SAEnum("beginner", "low", "medium", "high", "advanced", name="difficulty_profile_enum"),
        nullable=False,
    )
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime, nullable=True)
    status = Column(
        SAEnum("in_progress", "completed", "abandoned", name="quiz_status_enum"),
        server_default="in_progress",
    )


class QuizSessionQuestion(Base):
    __tablename__ = "quiz_session_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_session_id = Column(Integer, ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
