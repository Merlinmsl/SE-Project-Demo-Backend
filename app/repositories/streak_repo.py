"""
streak_repo.py — Repository layer for DailyStreak and DailyCompletion.

Follows the existing repository pattern in this project (see student_repo.py,
quiz_repository.py). All database access for the streak feature goes here;
the service layer calls these methods rather than querying SQLAlchemy directly.
"""

from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.daily_streak import DailyStreak
from app.models.daily_completion import DailyCompletion
from app.models.notification import Notification


class StreakRepository:
    """Data-access layer for streak-related tables."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # DailyStreak queries
    # ------------------------------------------------------------------

    def get_streak_by_user(self, user_id: int) -> Optional[DailyStreak]:
        """Return the streak record for a user, or None if it does not exist."""
        return (
            self.db.query(DailyStreak)
            .filter(DailyStreak.user_id == user_id)
            .first()
        )

    def get_streak_by_user_locked(self, user_id: int) -> Optional[DailyStreak]:
        """
        Return the streak record with a FOR UPDATE row lock.
        Use this inside a write transaction to prevent race conditions
        when multiple concurrent requests hit POST /streaks/complete.
        """
        return (
            self.db.query(DailyStreak)
            .with_for_update()
            .filter(DailyStreak.user_id == user_id)
            .first()
        )

    def create_streak(self, user_id: int) -> DailyStreak:
        """
        Create a fresh streak record for a first-time user and flush it
        so that subsequent queries in the same transaction can see it.
        Does NOT commit — the caller is responsible for committing.
        """
        streak = DailyStreak(
            user_id=user_id,
            current_streak=0,
            longest_streak=0,
            last_completed_date=None,
        )
        self.db.add(streak)
        self.db.flush()
        return streak

    def get_or_create_streak(self, user_id: int) -> DailyStreak:
        """
        Return the existing streak record or create one if it does not exist.
        Flushes after creation so the row is visible for later locked reads.
        """
        streak = self.get_streak_by_user(user_id)
        if not streak:
            streak = self.create_streak(user_id)
        return streak

    def get_broken_streaks(self, cutoff_date: date) -> List[DailyStreak]:
        """
        Return all streaks where last_completed_date <= cutoff_date AND
        current_streak > 0. Used by the cron job to find which users
        missed yesterday (i.e. their streak has just broken).

        Args:
            cutoff_date: Any streak not completed after this date is broken.
                         The cron passes (today - 2 days) so that streaks
                         last updated on or before that date are considered broken.
        """
        return (
            self.db.query(DailyStreak)
            .filter(
                DailyStreak.last_completed_date <= cutoff_date,
                DailyStreak.current_streak > 0,
            )
            .all()
        )

    # ------------------------------------------------------------------
    # DailyCompletion queries
    # ------------------------------------------------------------------

    def get_completions_by_user(self, user_id: int) -> List[DailyCompletion]:
        """Return all completion records for a user, newest first."""
        return (
            self.db.query(DailyCompletion)
            .filter(DailyCompletion.user_id == user_id)
            .order_by(DailyCompletion.completed_date.desc())
            .all()
        )

    def completion_exists_for_date(self, user_id: int, target_date: date) -> bool:
        """
        Return True if the user already has a DailyCompletion row for the
        given date. Used as a secondary idempotency check in the service.
        """
        return (
            self.db.query(DailyCompletion)
            .filter(
                DailyCompletion.user_id == user_id,
                DailyCompletion.completed_date == target_date,
            )
            .first()
            is not None
        )

    def create_completion(
        self,
        user_id: int,
        completed_date: date,
        tasks_completed: Optional[dict] = None,
    ) -> DailyCompletion:
        """
        Insert a DailyCompletion audit-trail row.
        Does NOT commit — caller commits after all streak writes are done.
        """
        completion = DailyCompletion(
            user_id=user_id,
            completed_date=completed_date,
            tasks_completed=tasks_completed or {},
        )
        self.db.add(completion)
        return completion

    # ------------------------------------------------------------------
    # Notification queries
    # ------------------------------------------------------------------

    def create_broken_streak_notification(
        self, user_id: int, prev_streak: int
    ) -> Notification:
        """
        Create a streak-broken notification record for a user.
        Does NOT commit — the cron/service commits in bulk after
        processing all affected users.
        """
        notif = Notification(
            user_id=user_id,
            title="Streak Broken 💔",
            message=(
                f"Oh no! Your {prev_streak}-day learning streak has been broken. "
                "Complete a task today to start a new one!"
            ),
        )
        self.db.add(notif)
        return notif

    def get_notifications_by_user(
        self, user_id: int, unread_only: bool = False
    ) -> List[Notification]:
        """Return notifications for a user (newest first), optionally filtered to unread."""
        q = self.db.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            q = q.filter(Notification.is_read == False)  # noqa: E712
        return q.order_by(Notification.created_at.desc()).all()

    def mark_notification_read(
        self, notification_id: int, user_id: int
    ) -> Optional[Notification]:
        """
        Mark a single notification as read. Returns the updated record, or
        None if the record does not belong to this user (security guard).
        """
        notif = (
            self.db.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .first()
        )
        if notif:
            notif.is_read = True
            self.db.commit()
            self.db.refresh(notif)
        return notif

    def mark_all_notifications_read(self, user_id: int) -> int:
        """
        Mark every unread notification as read for the given user.
        Returns the count of rows updated.
        """
        count = (
            self.db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.is_read == False,  # noqa: E712
            )
            .update({"is_read": True})
        )
        self.db.commit()
        return count
