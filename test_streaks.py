import os
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.db.base import Base
import app.models  # Ensures all models are loaded
from app.models.student import Student
from app.models.district import District
from app.models.province import Province
from app.models.grade import Grade
from app.models.daily_streak import DailyStreak
from app.models.daily_completion import DailyCompletion
from app.schemas.streak import StreakResponse
from app.services.streak_service import StreakService

engine = create_engine(os.environ["DATABASE_URL"], connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # create sample student
    student = Student(id=1, email="test@test.com", username="tester")
    db.add(student)
    db.commit()
    
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_streak_first_time(db_session):
    res = StreakService.complete_daily_tasks(db_session, 1, {"task": "first"})
    assert res["status"] == "streak_updated"
    assert res["current_streak"] == 1
    assert res["longest_streak"] == 1

def test_streak_consecutive(db_session):
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    
    # Pre-seed yesterday
    streak = DailyStreak(user_id=1, current_streak=1, longest_streak=1, last_completed_date=yesterday)
    db_session.add(streak)
    db_session.commit()
    
    res = StreakService.complete_daily_tasks(db_session, 1, {})
    assert res["status"] == "streak_updated"
    assert res["current_streak"] == 2
    assert res["longest_streak"] == 2

def test_streak_idempotent(db_session):
    today = datetime.now(timezone.utc).date()
    
    # Pre-seed today
    streak = DailyStreak(user_id=1, current_streak=2, longest_streak=2, last_completed_date=today)
    db_session.add(streak)
    db_session.commit()
    
    res = StreakService.complete_daily_tasks(db_session, 1, {})
    assert res["status"] == "already_completed"
    assert res["current_streak"] == 2
    
def test_streak_break(db_session):
    today = datetime.now(timezone.utc).date()
    two_days_ago = today - timedelta(days=2)
    
    # Pre-seed 2 days ago
    streak = DailyStreak(user_id=1, current_streak=5, longest_streak=5, last_completed_date=two_days_ago)
    db_session.add(streak)
    db_session.commit()
    
    res = StreakService.complete_daily_tasks(db_session, 1, {})
    assert res["status"] == "streak_updated"
    assert res["current_streak"] == 1
    assert res["longest_streak"] == 5

def test_get_history(db_session):
    today = datetime.now(timezone.utc).date()
    comp = DailyCompletion(user_id=1, completed_date=today, tasks_completed={"id": 123})
    db_session.add(comp)
    db_session.commit()
    
    hist = StreakService.get_history(db_session, 1)
    assert len(hist) == 1
    assert hist[0].completed_date == today
    assert hist[0].tasks_completed["id"] == 123
