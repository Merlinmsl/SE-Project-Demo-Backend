from __future__ import annotations
from enum import Enum
from sqlalchemy import String, Boolean, Text, SmallInteger, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class ResourceType(str, Enum):
    textbook = "textbook"
    past_paper = "past_paper"
    answers = "answers"
    notes = "notes"
    other = "other"

class Resource(Base):
    __tablename__ = "resources"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)

    type: Mapped[str] = mapped_column(ENUM(ResourceType, name="resource_type", create_type=False), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
