"""
BadgeService — Business logic for evaluating and awarding ranking badges.

Story : MIN-62 – Badge for Top 10 District Ranking
Commit: 4/11

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


# ── Badge-name mapping per district rank ──────────────────────────────────────
# Each key is the rank (1-based), each value is the badge name used in the DB.
# Ranks without an entry here will not trigger a badge award.

DISTRICT_RANK_BADGE_MAP: dict[int, str] = {
    1: "Top 10 District",
    2: "Top 10 District – Runner Up",
    3: "Top 10 District – Rank 3",
    4: "Top 10 District – Rank 4",
    # Ranks 5-10 will be added in future commits as their badge URLs are provided.
}


class BadgeService:
    def __init__(self):
        self.badge_repo = badge_repository

    def evaluate_district_ranking(self, db: Session, student_id: int) -> int | None:
        """
        Evaluate the student's district ranking based on total XP and award
        the appropriate Top 10 District badge if they qualify.

        This method is called automatically after every quiz submission so that
        badge awards happen in real-time without manual intervention.

        Returns
        -------
        The student's rank (int), or None if they don't have a district yet.
        """
        # 1. Fetch the student record directly
        student = db.query(Student).filter(Student.id == student_id).first()

        if not student or not student.district_id:
            return None

        # 2. Fetch the student's own total XP
        student_xp = (
            db.query(func.coalesce(func.sum(StudentSubjectStats.total_xp), 0))
            .filter(StudentSubjectStats.student_id == student_id)
            .scalar()
        ) or 0

        # 3. Compute the rank by counting how many students in the same district have MORE XP
        higher_rank_count = (
            db.query(StudentSubjectStats.student_id)
            .join(Student, Student.id == StudentSubjectStats.student_id)
            .filter(Student.district_id == student.district_id)
            .group_by(StudentSubjectStats.student_id)
            .having(func.sum(StudentSubjectStats.total_xp) > student_xp)
            .count()
        )

        rank = higher_rank_count + 1

        # 4. Determine which badge to award from the rank map
        badge_name = DISTRICT_RANK_BADGE_MAP.get(rank)

        # 5. Award the badge if they hit a recognized top rank
        if badge_name:
            badge = self.badge_repo.get_badge_by_name(badge_name, db)
            if badge:
                # award_badge is idempotent: it will safely skip if already held.
                self.badge_repo.award_badge(student_id, badge.id, db)

        return rank


# Singleton instance to be used across the app
badge_service = BadgeService()
