from sqlalchemy import (
    Column, Integer, Text, Boolean, ForeignKey,
    UniqueConstraint, ForeignKeyConstraint, CheckConstraint
)
from app.db.base import Base


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_session_id = Column(Integer, ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    selected_option_id = Column(Integer, nullable=True)
    short_answer_text = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    xp_earned = Column(Integer, default=0, nullable=False)
    bonus_xp = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("quiz_session_id", "question_id", name="uq_quiz_answer_session_question"),
        ForeignKeyConstraint(
            ["selected_option_id", "question_id"],
            ["question_options.id", "question_options.question_id"],
            name="fk_quiz_answer_option",
        ),
        CheckConstraint("xp_earned >= 0", name="quiz_answers_xp_earned_check"),
        CheckConstraint("bonus_xp >= 0", name="quiz_answers_bonus_xp_check"),
    )
