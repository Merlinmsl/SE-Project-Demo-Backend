from sqlalchemy import Column, Integer, BigInteger, Numeric, DateTime, ForeignKey, CheckConstraint
from datetime import datetime, timezone
from app.db.base import Base


class StudentSubjectStats(Base):
    __tablename__ = "student_subject_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    total_quizzes = Column(Integer, default=0)
    average_score = Column(Numeric(5, 2), default=0)
    total_xp = Column(Integer, default=0)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("average_score BETWEEN 0 AND 100"),
    )


class StudentTopicStats(Base):
    __tablename__ = "student_topic_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    attempt_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    accuracy_percentage = Column(Numeric(5, 2), default=0)

    __table_args__ = (
        CheckConstraint("accuracy_percentage BETWEEN 0 AND 100"),
    )
