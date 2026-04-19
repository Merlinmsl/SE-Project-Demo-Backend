import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.db.base import Base
from datetime import date, timedelta
from app.repositories.streak_repo import StreakRepository
from app.models.daily_streak import DailyStreak
from app.models.daily_completion import DailyCompletion
from app.models.notification import Notification

engine = create_engine(os.environ["DATABASE_URL"], connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def repo(db_session):
    return StreakRepository(db_session)

def test_get_streak_by_user_not_found(repo):
    streak = repo.get_streak_by_user(999)
    assert streak is None

def test_get_or_create_streak(repo, db_session):
    user_id = 2
    streak = repo.get_or_create_streak(user_id)
    assert streak is not None
    assert streak.user_id == user_id
    assert streak.current_streak == 0
    assert streak.longest_streak == 0
    
    # Second time should fetch the same record
    streak2 = repo.get_or_create_streak(user_id)
    assert streak2.id == streak.id

def test_get_broken_streaks(repo, db_session):
    today = date.today()
    two_days_ago = today - timedelta(days=2)
    user_id = 3
    
    streak = repo.create_streak(user_id)
    streak.current_streak = 5
    streak.last_completed_date = two_days_ago
    db_session.flush()
    
    broken_streaks = repo.get_broken_streaks(two_days_ago)
    assert len(broken_streaks) == 1
    assert broken_streaks[0].user_id == user_id

def test_create_broken_streak_notification(repo, db_session):
    user_id = 4
    prev_streak = 10
    notif = repo.create_broken_streak_notification(user_id, prev_streak)
    
    assert notif is not None
    assert notif.user_id == user_id
    assert notif.title == "Streak Broken 💔"
    assert str(prev_streak) in notif.message
    
def test_get_notifications_by_user(repo, db_session):
    user_id = 5
    notif1 = repo.create_broken_streak_notification(user_id, 3)
    notif2 = repo.create_broken_streak_notification(user_id, 2)
    db_session.flush()
    
    notifs = repo.get_notifications_by_user(user_id)
    assert len(notifs) >= 2
    
def test_mark_notification_read(repo, db_session):
    user_id = 6
    notif = repo.create_broken_streak_notification(user_id, 1)
    db_session.commit()
    db_session.refresh(notif)
    
    updated_notif = repo.mark_notification_read(notif.id, user_id)
    assert updated_notif is not None
    assert updated_notif.is_read is True
    
    # Try marking another user's notification
    invalid_notif = repo.mark_notification_read(notif.id, 999)
    assert invalid_notif is None

def test_mark_all_notifications_read(repo, db_session):
    user_id = 7
    repo.create_broken_streak_notification(user_id, 5)
    repo.create_broken_streak_notification(user_id, 2)
    db_session.commit()
    
    count = repo.mark_all_notifications_read(user_id)
    assert count == 2
    
    unread_notifs = repo.get_notifications_by_user(user_id, unread_only=True)
    assert len(unread_notifs) == 0
