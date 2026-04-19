"""
Badge Repository — MIN-61

Data-access layer for all badge-related DB operations.  Follows the same
session-injection pattern as the rest of the codebase (``db`` is passed in
per-call from the service or router so the repository itself is stateless and
reusable).

Responsibilities
----------------
* Look up ``Badge`` rows (by id, by name, or list all).
* Look up ``StudentBadge`` rows for a given student.
* Check whether a student already holds a specific badge.
* Grant a badge to a student (insert ``StudentBadge``).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.badge import Badge, StudentBadge


class BadgeRepository:
    """All database interactions for badges and student-badge awards.

    Methods are intentionally granular so callers in the service layer can
    compose exactly the queries they need without pulling unnecessary data.
    """

    # ──────────────────────────────────────────────────────────────────────────
    # Badge look-ups
    # ──────────────────────────────────────────────────────────────────────────

    def get_badge_by_id(self, db: Session, badge_id: int) -> Badge | None:
        """Return the ``Badge`` with the given primary key, or ``None``."""
        return db.query(Badge).filter(Badge.id == badge_id).first()

    def get_badge_by_name(self, db: Session, name: str) -> Badge | None:
        """Return the ``Badge`` whose ``name`` matches exactly, or ``None``.

        Used by :class:`~app.services.streak_badge_service.StreakBadgeService`
        to locate the "7-Day Streak" badge by its canonical name constant.
        """
        return db.query(Badge).filter(Badge.name == name).first()

    def list_all_badges(self, db: Session) -> list[Badge]:
        """Return every badge row ordered by ``id`` ascending."""
        return db.query(Badge).order_by(Badge.id).all()

    # ──────────────────────────────────────────────────────────────────────────
    # Student-badge look-ups
    # ──────────────────────────────────────────────────────────────────────────

    def get_student_badges(self, db: Session, student_id: int) -> list[StudentBadge]:
        """Return all ``StudentBadge`` rows for *student_id*, newest first.

        Callers can join / enrich with badge metadata as needed.
        """
        return (
            db.query(StudentBadge)
            .filter(StudentBadge.student_id == student_id)
            .order_by(StudentBadge.awarded_at.desc())
            .all()
        )

    def has_badge(self, db: Session, student_id: int, badge_id: int) -> bool:
        """Return ``True`` if the student already holds *badge_id*.

        Uses ``EXISTS``-style ``.first()`` so no full row is fetched.
        """
        return (
            db.query(StudentBadge)
            .filter(
                StudentBadge.student_id == student_id,
                StudentBadge.badge_id == badge_id,
            )
            .first()
        ) is not None

    def get_student_badge(
        self, db: Session, student_id: int, badge_id: int
    ) -> StudentBadge | None:
        """Return the specific ``StudentBadge`` join record, or ``None``."""
        return (
            db.query(StudentBadge)
            .filter(
                StudentBadge.student_id == student_id,
                StudentBadge.badge_id == badge_id,
            )
            .first()
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Badge award
    # ──────────────────────────────────────────────────────────────────────────

    def award_badge(
        self,
        db: Session,
        student_id: int,
        badge_id: int,
    ) -> tuple[StudentBadge, bool]:
        """Grant *badge_id* to *student_id* and return ``(record, newly_awarded)``.

        The operation is **idempotent**: if the student already holds the badge
        the existing ``StudentBadge`` row is returned with ``newly_awarded=False``.
        A savepoint is used so an ``IntegrityError`` from a concurrent insert
        does not invalidate the surrounding transaction.

        Parameters
        ----------
        db:
            Active SQLAlchemy session.
        student_id:
            PK of the student receiving the badge.
        badge_id:
            PK of the badge to award.

        Returns
        -------
        tuple[StudentBadge, bool]
            ``(student_badge_record, newly_awarded)``
        """
        # Fast path: already awarded
        existing = self.get_student_badge(db, student_id, badge_id)
        if existing is not None:
            return existing, False

        now = datetime.now(timezone.utc)
        record = StudentBadge(
            student_id=student_id,
            badge_id=badge_id,
            awarded_at=now,
        )

        try:
            db.begin_nested()   # savepoint
            db.add(record)
            db.flush()          # raise IntegrityError here if duplicate
        except IntegrityError:
            db.rollback()       # roll back to savepoint only
            existing = self.get_student_badge(db, student_id, badge_id)
            # existing will be non-None after the rollback
            return existing, False  # type: ignore[return-value]

        return record, True
