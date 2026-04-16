from typing import List, Optional
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from app.models.daily_streak import DailyStreak
from app.models.daily_completion import DailyCompletion
from app.repositories.streak_repo import StreakRepository


def get_today_utc() -> date:
    """Consistently get today's date in UTC as per requirements."""
    return datetime.now(timezone.utc).date()


class StreakService:
    @staticmethod
    def get_current_streak(db: Session, user_id: int) -> dict:
        repo = StreakRepository(db)
        streak = repo.get_streak_by_user(user_id)
        if not streak:
            return {"current_streak": 0, "longest_streak": 0, "last_completed_date": None}
        return {
            "current_streak": streak.current_streak,
            "longest_streak": streak.longest_streak,
            "last_completed_date": str(streak.last_completed_date) if streak.last_completed_date else None,
        }

    @staticmethod
    def complete_daily_tasks(db: Session, user_id: int, tasks: dict = None) -> dict:
        """
        Marks tasks as completed for the day and calculates the streak.
        Uses a simple single-transaction pattern to avoid flush/lock race conditions.
        """
        today = get_today_utc()
        yesterday = today - timedelta(days=1)

        # Get or create the streak record
        streak = db.query(DailyStreak).filter(DailyStreak.user_id == user_id).first()

        if not streak:
            streak = DailyStreak(
                user_id=user_id,
                current_streak=0,
                longest_streak=0,
                last_completed_date=None,
            )
            db.add(streak)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                # Concurrent request already created it — re-fetch
                streak = db.query(DailyStreak).filter(DailyStreak.user_id == user_id).first()
                if not streak:
                    raise HTTPException(status_code=500, detail="Failed to create streak record.")

        # Idempotency — already completed today, return current values
        if streak.last_completed_date == today:
            return {
                "status": "already_completed",
                "message": "Already completed today. No streak change.",
                "current_streak": streak.current_streak,
                "longest_streak": streak.longest_streak,
            }

        # Calculate streak
        if streak.last_completed_date == yesterday:
            streak.current_streak += 1
        else:
            # Streak broken or first completion ever — start fresh at 1
            streak.current_streak = 1

        streak.last_completed_date = today

        # Update longest streak record
        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak

        # Append audit entry
        completion = DailyCompletion(
            user_id=user_id,
            completed_date=today,
        )
        db.add(completion)

        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            import traceback
            print("==== STREAK COMMIT ERROR ====")
            traceback.print_exc()
            print("============================")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save streak: {str(exc)}",
            )

        return {
            "status": "streak_updated",
            "message": "Tasks completed, streak incremented.",
            "current_streak": streak.current_streak,
            "longest_streak": streak.longest_streak,
        }

    @staticmethod
    def get_history(db: Session, user_id: int) -> List[DailyCompletion]:
        repo = StreakRepository(db)
        return repo.get_completions_by_user(user_id)
