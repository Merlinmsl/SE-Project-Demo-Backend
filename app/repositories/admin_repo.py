from __future__ import annotations
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.student import Student

class AdminRepository:
    def __init__(self, db: Session):
        self.db = db

    def count_students(self) -> int:
        return int(self.db.scalar(select(func.count()).select_from(Student)) or 0)
