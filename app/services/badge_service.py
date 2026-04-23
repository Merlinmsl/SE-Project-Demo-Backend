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
# Matches the Supabase table 'badges' where ranking badges are 'Top X badge'
DISTRICT_RANK_BADGE_MAP: dict[int, str] = {
    1: "Top 1 badge",
    2: "Top 2 badge",
    3: "Top 3 badge",
    4: "Top 4 badge",
    5: "Top 5 badge",
    6: "Top 6 badge",
    7: "Top 7 badge",
    8: "Top 8 badge",
    9: "Top 9 badge",
    10: "Top 10 badge",
}


class BadgeService:
    def __init__(self):
        self.badge_repo = badge_repository

    def evaluate_district_ranking(self, db: Session, student_id: int) -> int | None:
        """
        Evaluate the student's district ranking based on total XP and award
        the appropriate Top X badge if they qualify.
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

    def evaluate_milestones(self, db: Session, student_id: int, days_gap: int = 0) -> list[dict]:
        """
        Evaluate various milestones (XP, Quiz counts, Time-based) and award badges.
        Returns a list of newly awarded badge info dicts.
        """
        from datetime import datetime
        from app.models.student_stats import StudentSubjectStats
        from sqlalchemy import func

        newly_awarded_badges = []

        # 1. Fetch Aggregate Stats
        stats = db.query(
            func.coalesce(func.sum(StudentSubjectStats.total_xp), 0).label("total_xp"),
            func.coalesce(func.sum(StudentSubjectStats.total_quizzes), 0).label("total_quizzes")
        ).filter(StudentSubjectStats.student_id == student_id).first()

        total_xp = stats.total_xp if stats else 0
        total_quizzes = stats.total_quizzes if stats else 0

        # 2. Define Milestone Criteria (Names aliased exactly to Supabase rows)
        milestones = [
            # Quiz Counts
            (total_quizzes >= 5, "quiz_beginner"),
            (total_quizzes >= 25, "quiz_explorer"),
            (total_quizzes >= 100, "quiz_master"),
            # XP Thresholds
            (total_xp >= 500, "xp_starter"),
            (total_xp >= 2000, "xp_grinder"),
            (total_xp >= 10000, "xp_legend"),
        ]

        # 3. Time-based: Night Owl (12 AM - 4 AM)
        current_hour = datetime.now().hour 
        if 0 <= current_hour < 4:
            milestones.append((True, "night_owl"))

        # 4. Inactivity: Comeback Hero (> 7 days)
        if days_gap > 7:
            milestones.append((True, "comeback_hero"))

        # 5. Evaluate and Award
        for is_eligible, badge_name in milestones:
            if not is_eligible:
                continue

            badge = self.badge_repo.get_badge_by_name(badge_name, db)
            if not badge:
                # Fallback to Title Case if snake_case not found (just in case)
                alt_name = badge_name.replace("_", " ").title()
                badge = self.badge_repo.get_badge_by_name(alt_name, db)
                if not badge:
                    continue

            # award_badge is idempotent
            _, newly_awarded = self.badge_repo.award_badge(student_id, badge.id, db)
            
            if newly_awarded:
                newly_awarded_badges.append({
                    "badge_id": badge.id,
                    "badge_name": badge.name,
                    "image_url": badge.image_url
                })

        return newly_awarded_badges


# Singleton instance to be used across the app
badge_service = BadgeService()
