from __future__ import annotations
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from app.models.subject import Subject, StudentSubject

class SubjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_subjects_for_grade(self, grade_id: int) -> list[Subject]:
        return list(self.db.scalars(select(Subject).where(Subject.grade_id == grade_id).order_by(Subject.name)))

    def list_selected_subjects(self, student_id) -> list[StudentSubject]:
        return list(self.db.scalars(select(StudentSubject).where(StudentSubject.student_id == student_id)))

    def replace_selected_subjects(self, student_id, subject_ids: list[int]) -> None:
        self.db.execute(delete(StudentSubject).where(StudentSubject.student_id == student_id))
        for sid in subject_ids:
            self.db.add(StudentSubject(student_id=student_id, subject_id=sid))
        self.db.commit()

    def is_subject_selected(self, student_id, subject_id: int) -> bool:
        q = select(StudentSubject).where(StudentSubject.student_id == student_id, StudentSubject.subject_id == subject_id)
        return self.db.scalar(q) is not None
