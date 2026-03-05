from __future__ import annotations
import re
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.student import Student
from app.core.security import AuthUser

PENDING_PREFIX = "pending_"

def _safe_username(base: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9_]", "_", (base or "")).strip("_")
    return (base or "user")[:50]

class StudentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_clerk_id(self, clerk_user_id: str) -> Student | None:
        return self.db.scalar(select(Student).where(Student.clerk_user_id == clerk_user_id))

    def get_by_username(self, username: str) -> Student | None:
        return self.db.scalar(select(Student).where(Student.username == username))

    def create_if_missing(self, user: AuthUser) -> Student:
        existing = self.get_by_clerk_id(user.clerk_user_id)
        if existing:
            if user.email and existing.email != user.email:
                existing.email = user.email
                self.db.commit()
            return existing

        suffix = user.clerk_user_id[-8:] if user.clerk_user_id else "newuser1"
        placeholder = (PENDING_PREFIX + suffix)[:50]

        st = Student(
            clerk_user_id=user.clerk_user_id,
            email=user.email,
            username=placeholder,
            profile_completed=False,
        )
        self.db.add(st)
        self.db.commit()
        self.db.refresh(st)
        return st

    def update(self, student: Student, **fields) -> Student:
        for k, v in fields.items():
            setattr(student, k, v)
        self.db.commit()
        self.db.refresh(student)
        return student
