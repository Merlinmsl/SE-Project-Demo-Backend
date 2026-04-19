"""
BadgeRepository — Data access layer for badges and student_badges tables.

Story : MIN-62  – Badge for Top 10 District Ranking
Commit: 2/11

Responsibilities
----------------
- Look up badge definitions (by id or name).
- Check whether a student already holds a specific badge.
- Award a badge to a student (idempotent — safe to call even if already held).
- Retrieve all badges a student has earned (with full badge metadata).
- List all available badge definitions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.badge import Badge, StudentBadge


class BadgeRepository:
    """All database interactions for the badges and student_badges tables."""

    # ── Badge look-ups ────────────────────────────────────────────────────────

    def get_badge_by_id(self, badge_id: int, db: Session) -> Optional[Badge]:
        """Return a Badge row by its primary key, or None if not found."""
        return db.query(Badge).filter(Badge.id == badge_id).first()

    def get_badge_by_name(self, name: str, db: Session) -> Optional[Badge]:
        """Return a Badge row by its unique name, or None if not found."""
        return db.query(Badge).filter(Badge.name == name).first()

    def get_all_badges(self, db: Session) -> list[Badge]:
        """Return all badge definitions ordered by id."""
        return db.query(Badge).order_by(Badge.id).all()

    # ── Student-Badge look-ups ────────────────────────────────────────────────

    def get_student_badge(
        self, student_id: int, badge_id: int, db: Session
    ) -> Optional[StudentBadge]:
        """Return the StudentBadge join-row if the student holds this badge."""
        return (
            db.query(StudentBadge)
            .filter(
                StudentBadge.student_id == student_id,
                StudentBadge.badge_id == badge_id,
            )
            .first()
        )

    def student_has_badge(
        self, student_id: int, badge_id: int, db: Session
    ) -> bool:
        """Return True if the student already holds the badge."""
        return self.get_student_badge(student_id, badge_id, db) is not None

    def get_badges_for_student(
        self, student_id: int, db: Session
    ) -> list[tuple[StudentBadge, Badge]]:
        """Return all (StudentBadge, Badge) pairs for a student, newest first."""
        return (
            db.query(StudentBadge, Badge)
            .join(Badge, Badge.id == StudentBadge.badge_id)
            .filter(StudentBadge.student_id == student_id)
            .order_by(StudentBadge.awarded_at.desc())
            .all()
        )

    # ── Award logic ───────────────────────────────────────────────────────────

    def award_badge(
        self, student_id: int, badge_id: int, db: Session
    ) -> tuple[StudentBadge, bool]:
        """Award a badge to a student.

        Idempotent — if the student already holds the badge the existing row
        is returned and ``awarded_now`` is False.

        Returns
        -------
        (student_badge_row, awarded_now)
            awarded_now is True only when a *new* award record was created.
        """
        existing = self.get_student_badge(student_id, badge_id, db)
        if existing:
            return existing, False

        new_record = StudentBadge(
            student_id=student_id,
            badge_id=badge_id,
            awarded_at=datetime.now(timezone.utc),
        )
        db.add(new_record)
        try:
            db.flush()          # write to DB within the current transaction
        except IntegrityError:
            # Race condition: another request already inserted this row
            db.rollback()
            existing = self.get_student_badge(student_id, badge_id, db)
            return existing, False

        return new_record, True


# Singleton instance — import this in services and API routes
badge_repository = BadgeRepository()
