from sqlalchemy import (
    Column, BigInteger, Integer, String, Text, Boolean,
    DateTime, ForeignKey, Enum as SAEnum
)
from datetime import datetime, timezone
from app.db.base import Base


class Resource(Base):
    __tablename__ = "resources"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    type = Column(
        SAEnum("textbook", "past_paper", "notes", "other", "answers", name="resource_type"),
        nullable=False,
    )
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    file_url = Column(Text, nullable=True)
    storage_path = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
