from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.student import Student
from app.repositories.student_repo import PENDING_PREFIX
from app.models.student import Student
from app.repositories.student_repo import PENDING_PREFIX
from app.repositories.subject_repo import SubjectRepository


class ProfileService:
    """Profile completion rules (MIN-16).

    SOLID:
    - Single Responsibility: encapsulates completion rules only.
    """

    def __init__(self, db: Session):
        self.subjects = SubjectRepository(db)

    def recompute_profile_completed(self, student: Student) -> bool:
        # DB-backed required fields
        if not student.email or not student.full_name:
            return False
        if not student.username or student.username.startswith(PENDING_PREFIX):
            return False
        if not student.grade_id or not student.district_id or not student.avatar_key:
            return False

        # Subjects (at least one)
        selected = self.subjects.list_selected_subjects(student.id)
        if len(selected) == 0:
            return False

        return True
