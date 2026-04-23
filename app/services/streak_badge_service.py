"""
Streak Badge Service — MIN-61

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

from sqlalchemy.orm import Session

from app.models.study_streak import StudyStreak
from app.repositories.badge_repo import BadgeRepository

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

#: Exact name used when the 7-day-streak badge was inserted into ``badges``.
STREAK_7_BADGE_NAME: str = "7 day streak"

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

    All DB access is delegated to :class:`~app.repositories.badge_repo.BadgeRepository`
    so the service remains decoupled from SQLAlchemy query mechanics and is
    easy to unit-test with a mocked repository.

    Parameters
    ----------
    db:
        Active SQLAlchemy ``Session`` provided by FastAPI's dependency
        injection chain (``get_db`` dependency).
    badge_repo:
        Optional pre-constructed :class:`BadgeRepository` instance.  When
        omitted a default instance is created automatically (production path).
    """

    def __init__(
        self,
        db: Session,
        badge_repo: BadgeRepository | None = None,
    ) -> None:
        self._db = db
        self._badge_repo = badge_repo or BadgeRepository()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_and_award(self, student_id: int) -> BadgeAwardResult:
        """Check the student's streak and award the badge if eligible.

        The method:

        1. Looks up the student's ``current_streak`` in ``study_streaks``.
        2. Returns early (no-op) if the streak is below :data:`STREAK_THRESHOLD`.
        3. Looks up the badge row by :data:`STREAK_7_BADGE_NAME` via the repo.
        4. Delegates the idempotent award insert to
           :meth:`BadgeRepository.award_badge`.

        Parameters
        ----------
        student_id:
            The ``students.id`` of the authenticated student.

        Returns
        -------
        BadgeAwardResult
            Structured object describing whether the badge was newly awarded
            and containing badge metadata for the frontend notification.
        """
        streak = self._get_streak(student_id)
        if streak is None or streak.current_streak < STREAK_THRESHOLD:
            return BadgeAwardResult(newly_awarded=False)

        badge = self._badge_repo.get_badge_by_name(self._db, STREAK_7_BADGE_NAME)
        if badge is None:
            # Badge not seeded — fail silently so quiz submission still works.
            return BadgeAwardResult(newly_awarded=False)

        student_badge, newly_awarded = self._badge_repo.award_badge(
            self._db, student_id, badge.id
        )

        return BadgeAwardResult(
            newly_awarded=newly_awarded,
            badge_id=badge.id,
            badge_name=badge.name,
            image_url=badge.image_url,
            awarded_at=student_badge.awarded_at,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_streak(self, student_id: int) -> StudyStreak | None:
        """Fetch the streak record for *student_id*, or ``None`` if missing."""
        return (
            self._db.query(StudyStreak)
            .filter(StudyStreak.student_id == student_id)
            .first()
        )
