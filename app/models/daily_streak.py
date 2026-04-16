from sqlalchemy import Column, BigInteger, Integer, Date, DateTime, ForeignKey, text
from sqlalchemy.sql import func
from app.db.base import Base

class DailyStreak(Base):
    __tablename__ = "daily_streaks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    current_streak = Column(Integer, default=0, nullable=False)
    longest_streak = Column(Integer, default=0, nullable=False)
    last_completed_date = Column(Date, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
