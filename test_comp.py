import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.student import Student
from app.services.streak_service import StreakService
import traceback

try:
    load_dotenv()
    db_url = os.getenv("DATABASE_URI") or os.getenv("DATABASE_URL")
    engine = create_engine(db_url, connect_args={"connect_timeout": 15})
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    result = StreakService.complete_daily_tasks(db, 14, {})
    print(result)
except Exception as e:
    print("AN ERROR OCCURRED:")
    traceback.print_exc()
