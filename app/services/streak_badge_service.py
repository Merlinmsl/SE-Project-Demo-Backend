"""
Streak Badge Service — MIN-282

Encapsulates the business logic for awarding the "7-Day Streak" badge to a
student.  The service is intentionally kept thin and side-effect free aside
from DB writes, making it straightforward to unit-test.

Award rules
-----------
* The badge named exactly ``STREAK_7_BADGE_NAME`` must already exist in the
  ``badges`` table (seeded into Supabase). 
* The badge is awarded **once** the student's ``current_streak`` reaches
  ``STREAK_THRESHOLD`` (7) days.
* Subsequent calls with the same student are idempotent: if the badge has
  already been granted the service returns ``False`` for ``newly_awarded``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.badge import Badge, StudentBadge
from app.models.study_streak import StudyStreak

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

#: Exact name used when the 7-day-streak badge was inserted into ``badges``.
STREAK_7_BADGE_NAME: str = "7-Day Streak"

#: Number of consecutive study days required to earn the badge.
STREAK_THRESHOLD: int = 7


# ──────────────────────────────────────────────────────────────────────────────
# Data transfer objects
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class BadgeAwardResult:
    """Result returned by :meth:`StreakBadgeService.check_and_award`.

    Attributes
    ----------
    newly_awarded:
        ``True`` when the badge was awarded during *this* call.
        ``False`` when the student had already earned it, or when the streak
        threshold has not been reached yet.
    badge_id:
        Database PK of the badge, or ``None`` if the badge row was not found.
    badge_name:
        Human-readable badge name (e.g. ``"7-Day Streak"``).
    image_url:
        Publicly accessible URL of the badge artwork, or ``None``.
    awarded_at:
        UTC timestamp of the award (new or existing), or ``None`` if the
        student hasn't earned the badge.
    """

    newly_awarded: bool
    badge_id: int | None = None
    badge_name: str | None = None
    image_url: str | None = None
    awarded_at: datetime | None = None


# ──────────────────────────────────────────────────────────────────────────────
# Service
# ──────────────────────────────────────────────────────────────────────────────


class StreakBadgeService:
    """Checks and awards the 7-Day Streak badge for a student.

    Parameters
    ----------
    db:
        Active SQLAlchemy ``Session`` provided by FastAPI's dependency
        injection chain (``get_db`` dependency).
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_and_award(self, student_id: int) -> BadgeAwardResult:
        """Check the student's streak and award the badge if eligible.

        The method:

        1. Looks up the student's ``current_streak`` in ``study_streaks``.
        2. Returns early (no-op) if the streak is below :data:`STREAK_THRESHOLD`.
        3. Looks up the badge row by :data:`STREAK_7_BADGE_NAME`.
        4. Attempts to insert a ``student_badges`` row; if the unique
           constraint fires the badge was already awarded so the insert is
           silently rolled back and the existing award record is returned.

        Parameters
        ----------
        student_id:
            The ``students.id`` of the authenticated student.

        Returns
        -------
        BadgeAwardResult
            Structured object describing whether the badge was newly awarded
            and containing badge metadata for the frontend.
        """
        streak = self._get_streak(student_id)
        if streak is None or streak.current_streak < STREAK_THRESHOLD:
            return BadgeAwardResult(newly_awarded=False)

        badge = self._get_badge()
        if badge is None:
            # Badge not seeded — fail silently so quiz submission still works.
            return BadgeAwardResult(newly_awarded=False)

        return self._award_badge(student_id, badge)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_streak(self, student_id: int) -> StudyStreak | None:
        """Fetch the streak record for *student_id*, or ``None`` if missing."""
        return (
            self._db.query(StudyStreak)
            .filter(StudyStreak.student_id == student_id)
            .first()
        )

    def _get_badge(self) -> Badge | None:
        """Fetch the 7-Day Streak badge row from the database."""
        return (
            self._db.query(Badge)
            .filter(Badge.name == STREAK_7_BADGE_NAME)
            .first()
        )

    def _award_badge(self, student_id: int, badge: Badge) -> BadgeAwardResult:
        """Try to insert a ``student_badges`` row; handle duplicate gracefully.

        Uses a savepoint so that an ``IntegrityError`` (duplicate award) does
        not invalidate the surrounding transaction.
        """
        # Check first whether the student already holds the badge to avoid
        # unnecessary savepoints on the happy path.
        existing = (
            self._db.query(StudentBadge)
            .filter(
                StudentBadge.student_id == student_id,
                StudentBadge.badge_id == badge.id,
            )
            .first()
        )

        if existing is not None:
            return BadgeAwardResult(
                newly_awarded=False,
                badge_id=badge.id,
                badge_name=badge.name,
                image_url=badge.image_url,
                awarded_at=existing.awarded_at,
            )

        # New award — insert inside a savepoint to remain safe.
        now = datetime.now(timezone.utc)
        student_badge = StudentBadge(
            student_id=student_id,
            badge_id=badge.id,
            awarded_at=now,
        )
        try:
            self._db.begin_nested()  # savepoint
            self._db.add(student_badge)
            self._db.flush()         # propagate to DB within transaction
        except IntegrityError:
            self._db.rollback()      # roll back to savepoint only
            existing = (
                self._db.query(StudentBadge)
                .filter(
                    StudentBadge.student_id == student_id,
                    StudentBadge.badge_id == badge.id,
                )
                .first()
            )
            return BadgeAwardResult(
                newly_awarded=False,
                badge_id=badge.id,
                badge_name=badge.name,
                image_url=badge.image_url,
                awarded_at=existing.awarded_at if existing else now,
            )

        return BadgeAwardResult(
            newly_awarded=True,
            badge_id=badge.id,
            badge_name=badge.name,
            image_url=badge.image_url,
            awarded_at=now,
        )
