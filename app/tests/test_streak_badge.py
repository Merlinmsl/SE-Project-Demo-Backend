"""Unit tests for the StreakBadgeService logic."""

from unittest.mock import Mock
from datetime import datetime

from app.services.streak_badge_service import (
    StreakBadgeService,
    STREAK_THRESHOLD,
    STREAK_7_BADGE_NAME,
)
from app.models.badge import Badge, StudentBadge
from app.models.study_streak import StudyStreak


def test_streak_below_threshold():
    """Badge should not be awarded if current streak is below the threshold."""
    db_mock = Mock()
    badge_repo_mock = Mock()
    
    # Mock _get_streak natively or let query chain work
    # Service uses: self._db.query(StudyStreak).filter(...).first()
    query_mock = Mock()
    filter_mock = Mock()
    db_mock.query.return_value = query_mock
    query_mock.filter.return_value = filter_mock
    
    # Return a streak below threshold
    streak = StudyStreak(current_streak=STREAK_THRESHOLD - 1)
    filter_mock.first.return_value = streak
    
    service = StreakBadgeService(db_mock, badge_repo_mock)
    result = service.check_and_award(123)
    
    assert result.newly_awarded is False
    badge_repo_mock.get_badge_by_name.assert_not_called()


def test_badge_not_seeded():
    """If the badge is not in the database, it fails gracefully without error."""
    db_mock = Mock()
    badge_repo_mock = Mock()
    
    # Mock streak above threshold
    query_mock = Mock()
    filter_mock = Mock()
    db_mock.query.return_value = query_mock
    query_mock.filter.return_value = filter_mock
    
    streak = StudyStreak(current_streak=STREAK_THRESHOLD)
    filter_mock.first.return_value = streak
    
    # Mock badge repo: badge not found
    badge_repo_mock.get_badge_by_name.return_value = None
    
    service = StreakBadgeService(db_mock, badge_repo_mock)
    result = service.check_and_award(123)
    
    assert result.newly_awarded is False
    badge_repo_mock.award_badge.assert_not_called()


def test_badge_awarded_first_time():
    """Award is successful and returns full metadata if student hasn't earned it yet."""
    db_mock = Mock()
    badge_repo_mock = Mock()
    
    # Mock streak above threshold
    query_mock = Mock()
    filter_mock = Mock()
    db_mock.query.return_value = query_mock
    query_mock.filter.return_value = filter_mock
    
    streak = StudyStreak(current_streak=STREAK_THRESHOLD)
    filter_mock.first.return_value = streak
    
    # Mock badge
    badge = Badge(id=1, name=STREAK_7_BADGE_NAME, image_url="http://test.com/badge.png")
    badge_repo_mock.get_badge_by_name.return_value = badge
    
    # Mock successful award
    now = datetime.now()
    student_badge = StudentBadge(student_id=123, badge_id=1, awarded_at=now)
    badge_repo_mock.award_badge.return_value = (student_badge, True)
    
    service = StreakBadgeService(db_mock, badge_repo_mock)
    result = service.check_and_award(123)
    
    assert result.newly_awarded is True
    assert result.badge_id == 1
    assert result.badge_name == STREAK_7_BADGE_NAME
    assert result.image_url == "http://test.com/badge.png"
    assert result.awarded_at == now
    badge_repo_mock.award_badge.assert_called_once_with(db_mock, 123, 1)


def test_badge_already_awarded():
    """Service handles idempotency correctly if badge was already awarded in the past."""
    db_mock = Mock()
    badge_repo_mock = Mock()
    
    # Mock streak above threshold
    query_mock = Mock()
    filter_mock = Mock()
    db_mock.query.return_value = query_mock
    query_mock.filter.return_value = filter_mock
    
    streak = StudyStreak(current_streak=STREAK_THRESHOLD)
    filter_mock.first.return_value = streak
    
    # Mock badge
    badge = Badge(id=1, name=STREAK_7_BADGE_NAME, image_url="http://test.com/badge.png")
    badge_repo_mock.get_badge_by_name.return_value = badge
    
    # Mock duplicate award response from repo
    past_date = datetime.now()
    student_badge = StudentBadge(student_id=123, badge_id=1, awarded_at=past_date)
    badge_repo_mock.award_badge.return_value = (student_badge, False)
    
    service = StreakBadgeService(db_mock, badge_repo_mock)
    result = service.check_and_award(123)
    
    assert result.newly_awarded is False
    assert result.badge_id == 1
    assert result.awarded_at == past_date
