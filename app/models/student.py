from __future__ import annotations
from sqlalchemy import String, Boolean, SmallInteger, BigInteger, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.models.meta import District, Grade

class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    clerk_user_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(150), nullable=True)

    username: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)

    avatar_key: Mapped[str | None] = mapped_column(String(30), nullable=True)
    grade_id: Mapped[int | None] = mapped_column(SmallInteger, ForeignKey("grades.id", ondelete="SET NULL"), nullable=True)
    district_id: Mapped[int | None] = mapped_column(SmallInteger, ForeignKey("districts.id", ondelete="SET NULL"), nullable=True)

    profile_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[object] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[object] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    district: Mapped[District | None] = relationship("District", lazy="joined")
    grade: Mapped[Grade | None] = relationship("Grade", lazy="joined")
