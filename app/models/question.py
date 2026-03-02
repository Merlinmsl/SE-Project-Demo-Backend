from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, DateTime,
    ForeignKey, Enum as SAEnum, CheckConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    difficulty = Column(SAEnum("easy", "medium", "hard", name="difficulty_level"), nullable=False)
    type = Column(
        SAEnum("mcq", name="question_type_enum"),
        nullable=False,
        server_default="mcq"
    )
    question_text = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    xp_value = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(BigInteger, ForeignKey("admins.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("xp_value > 0", name="questions_xp_value_check"),
    )

    # Relationships
    options = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan", lazy="joined")


class QuestionOption(Base):
    __tablename__ = "question_options"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)

    # Relationships
    question = relationship("Question", back_populates="options")
