from sqlalchemy import Column, BigInteger, Integer, Text, String, DateTime, ForeignKey
from datetime import datetime, timezone
from app.db.base import Base


class AiChatLog(Base):
    __tablename__ = "ai_chat_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    student_id = Column(BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    session_id = Column(String(64), nullable=True)
    question = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    matched = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
