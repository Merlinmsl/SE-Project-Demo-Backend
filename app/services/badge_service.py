"""
BadgeService — Business logic for evaluating and awarding ranking badges.

Story : MIN-62 – Badge for Top 10 District Ranking
Commit: 3/11

Responsibilities
----------------
- Calculate a student's rank within their district.
- Automatically award the corresponding "Top 10 District" badge if eligible.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.student import Student
from app.models.student_stats import StudentSubjectStats
from app.repositories.badge_repository import badge_repository
from app.repositories.student_repo import StudentRepository


class BadgeService:
    def __init__(self):
        self.badge_repo = badge_repository

    def evaluate_district_ranking(self, db: Session, student_id: int) -> int | None:
        """
        Evaluate the student's district ranking based on total XP and award
        the appropriate Top 10 District badge if they qualify.

        Returns
        -------
        The student's rank (int), or None if they don't have a district yet.
        """
        st_repo = StudentRepository(db)
        student = st_repo.get_student_by_id(db, student_id)
        
        if not student or not student.district_id:
            return None

        # 1. Fetch the student's own total XP
        student_xp = (
            db.query(func.coalesce(func.sum(StudentSubjectStats.total_xp), 0))
            .filter(StudentSubjectStats.student_id == student_id)
            .scalar()
        ) or 0

        # If a student has no XP yet, we can technically still rank them, but
        # usually 0 XP means they just started. We'll proceed with rank calc.

        # 2. Compute the rank by counting how many students in the same district have MORE XP
        higher_rank_count = (
            db.query(StudentSubjectStats.student_id)
            .join(Student, Student.id == StudentSubjectStats.student_id)
            .filter(Student.district_id == student.district_id)
            .group_by(StudentSubjectStats.student_id)
            .having(func.sum(StudentSubjectStats.total_xp) > student_xp)
            .count()
        )

        rank = higher_rank_count + 1

        # 3. Determine which badge to award depending on the rank
        badge_name = None
        if rank == 1:
            badge_name = "Top 10 District"
        elif rank == 2:
            badge_name = "Top 10 District – Runner Up"
        elif rank == 3:
            badge_name = "Top 10 District – Rank 3"
        elif rank <= 10:
            # We'll add condition mapping for Rank 4-10 in future commits.
            pass

        # 4. Award the badge if they hit a recognized top rank
        if badge_name:
            badge = self.badge_repo.get_badge_by_name(badge_name, db)
            if badge:
                # award_badge is idempotent: it will safely skip if they already have it.
                self.badge_repo.award_badge(student_id, badge.id, db)

        return rank


# Singleton instance to be used across the app
badge_service = BadgeService()
