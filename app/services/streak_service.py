from typing import List, Optional
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session
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
            "last_completed_date": streak.last_completed_date
        }

    @staticmethod
    def complete_daily_tasks(db: Session, user_id: int, tasks: dict = None) -> dict:
        """
        Marks tasks as completed for the day and calculates the streak.
        Uses ROW LOCKING explicitly to prevent concurrent request race conditions.
        """
        repo = StreakRepository(db)
        today = get_today_utc()
        yesterday = today - timedelta(days=1)
        
        # 1. Ensure a record exists before trying to lock it
        repo.get_or_create_streak(user_id)
        
        # 2. Lock the row for updates -> FOR UPDATE
        streak = repo.get_streak_by_user_locked(user_id)
        
        if not streak:
            raise HTTPException(status_code=500, detail="Failed to acquire streak record.")

        status_msg = "streak_updated"
        message = "Tasks completed, streak incremented."

        # idempotency check
        if streak.last_completed_date == today:
            status_msg = "already_completed"
            message = "Already completed today. No streak change."
        else:
            # 3. Calculation Logic
            if streak.last_completed_date == yesterday:
                streak.current_streak += 1
            else:
                # the streak breaks if last_completed_date > yesterday or None
                streak.current_streak = 1
                
            streak.last_completed_date = today

            # check new record
            if streak.current_streak > streak.longest_streak:
                streak.longest_streak = streak.current_streak
                
            # Log completion
            # Only create completion if we actually updated the streak
            repo.create_completion(user_id, today, tasks)

        db.commit()

        return {
            "status": status_msg,
            "message": message,
            "current_streak": streak.current_streak,
            "longest_streak": streak.longest_streak
        }

    @staticmethod
    def get_history(db: Session, user_id: int) -> List[DailyCompletion]:
        repo = StreakRepository(db)
        return repo.get_completions_by_user(user_id)
