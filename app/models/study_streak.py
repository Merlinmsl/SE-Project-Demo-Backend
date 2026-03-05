from sqlalchemy import Column, BigInteger, Integer, Date, ForeignKey
from app.db.base import Base


class StudyStreak(Base):
    __tablename__ = "study_streaks"

    student_id = Column(BigInteger, ForeignKey("students.id", ondelete="CASCADE"), primary_key=True)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity_date = Column(Date, nullable=True)
