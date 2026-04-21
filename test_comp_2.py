import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import EVERYTHING to ensure declarative base registers all foreign keys
from app.models.student import Student
from app.models.daily_streak import DailyStreak
from app.models.daily_completion import DailyCompletion
from app.models.notification import Notification

from app.services.streak_service import StreakService
import traceback

try:
    load_dotenv()
    db_url = os.getenv("DATABASE_URI") or os.getenv("DATABASE_URL")
    engine = create_engine(db_url, connect_args={"options": "-c statement_timeout=15000", "keepalives": 1})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    print("Testing completion logic...")
    result = StreakService.complete_daily_tasks(db, 14, {})
    print("SUCCESS", result)
except Exception as e:
    print("==== STREAK SERVICE ERROR ====")
    traceback.print_exc()
