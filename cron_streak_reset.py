import os
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.daily_streak import DailyStreak
from app.models.notification import Notification

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found in environment.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def run_cron():
    db = SessionLocal()
    try:
        # Create notification table if it doesn't exist (safety)
        Base.metadata.create_all(bind=engine, tables=[Notification.__table__])
        
        today = datetime.now(timezone.utc).date()
        two_days_ago = today - timedelta(days=2)
        
        # Find broken streaks: last_completed_date is 2+ days ago AND current_streak > 0
        # Also need to handle cases where it was missed yesterday, meaning it breaks today
        # Technically "missed yesterday" means last_completed_date <= today - 2 days
        
        broken_streaks = db.query(DailyStreak).filter(
            DailyStreak.last_completed_date <= two_days_ago,
            DailyStreak.current_streak > 0
        ).all()
        
        print(f"Found {len(broken_streaks)} broken streaks. Processing...")
        
        notifications = []
        for streak in broken_streaks:
            # 1. Reset streak
            prev_streak = streak.current_streak
            streak.current_streak = 0
            
            # 2. Create notification
            notif = Notification(
                user_id=streak.user_id,
                title="Streak Broken 💔",
                message=f"Oh no! Your {prev_streak}-day learning streak has been broken. Complete a task today to start a new one!"
            )
            notifications.append(notif)
            db.add(notif)
            
        db.commit()
        print(f"Successfully reset {len(broken_streaks)} streaks and created notifications.")
        
    except Exception as e:
        db.rollback()
        print(f"Error running cron logic: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print(f"[{datetime.now(timezone.utc).isoformat()}] Running daily streak cron job...")
    run_cron()
    print("Done.")
