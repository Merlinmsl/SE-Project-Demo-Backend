from __future__ import annotations
from sqlalchemy import String, Boolean, SmallInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class Province(Base):
    __tablename__ = "provinces"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

class District(Base):
    __tablename__ = "districts"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    province_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("provinces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    province: Mapped[Province] = relationship("Province", lazy="joined")

class Grade(Base):
    __tablename__ = "grades"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
