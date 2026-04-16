import os
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.notification import Notification
from app.repositories.streak_repo import StreakRepository

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
        
        repo = StreakRepository(db)
        # Find broken streaks: last_completed_date is <= 2 days ago AND current_streak > 0
        broken_streaks = repo.get_broken_streaks(two_days_ago)
        
        print(f"Found {len(broken_streaks)} broken streaks. Processing...")
        
        for streak in broken_streaks:
            # 1. Reset streak
            prev_streak = streak.current_streak
            streak.current_streak = 0
            
            # 2. Create notification
            repo.create_broken_streak_notification(streak.user_id, prev_streak)
            
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
