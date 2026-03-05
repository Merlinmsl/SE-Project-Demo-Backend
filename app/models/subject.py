from __future__ import annotations
from sqlalchemy import String, SmallInteger, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    grade_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("grades.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

class StudentSubject(Base):
    __tablename__ = "student_subjects"
    student_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("students.id", ondelete="CASCADE"), primary_key=True)
    subject_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True)

    subject: Mapped[Subject] = relationship("Subject", lazy="joined")
