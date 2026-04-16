from sqlalchemy import Column, BigInteger, Integer, Date, ForeignKey, JSON
from app.db.base import Base

class DailyCompletion(Base):
    __tablename__ = "daily_completions"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    user_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    completed_date = Column(Date, nullable=False, index=True)
    tasks_completed = Column(JSON, nullable=True)  # Stores audit trail of tasks completed
