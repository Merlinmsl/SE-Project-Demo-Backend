import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

from app.models.badge import Badge, StudentBadge
from app.repositories.badge_repository import BadgeRepository
from app.services.badge_service import BadgeService


@pytest.fixture
def db_session_mock():
    return MagicMock(spec=Session)

@pytest.fixture
def badge_repo():
    return BadgeRepository()

@pytest.fixture
def badge_service(badge_repo):
    service = BadgeService()
    service.badge_repo = badge_repo
    return service

# ── BadgeRepository Tests ──────────────────────────────────────────────────────

def test_get_badge_by_id(badge_repo, db_session_mock):
    mock_badge = Badge(id=1, name="Test Badge")
    db_session_mock.query().filter().first.return_value = mock_badge
    
    result = badge_repo.get_badge_by_id(1, db_session_mock)
    assert result == mock_badge

def test_get_badge_by_name(badge_repo, db_session_mock):
    mock_badge = Badge(id=1, name="Top 10 District")
    db_session_mock.query().filter().first.return_value = mock_badge
    
    result = badge_repo.get_badge_by_name("Top 10 District", db_session_mock)
    assert result == mock_badge

def test_award_badge_new(badge_repo, db_session_mock):
    # Mock that the student currently does NOT have the badge
    db_session_mock.query().filter().first.return_value = None
    
    new_record, awarded_now = badge_repo.award_badge(student_id=42, badge_id=1, db=db_session_mock)
    
    assert awarded_now is True
    assert new_record.student_id == 42
    assert new_record.badge_id == 1
    db_session_mock.add.assert_called_once_with(new_record)
    db_session_mock.flush.assert_called_once()

def test_award_badge_already_earned_idempotent(badge_repo, db_session_mock):
    # Mock that the student ALREADY has the badge
    existing_sb = StudentBadge(student_id=42, badge_id=1)
    db_session_mock.query().filter().first.return_value = existing_sb
    
    record, awarded_now = badge_repo.award_badge(student_id=42, badge_id=1, db=db_session_mock)
    
    assert awarded_now is False
    assert record == existing_sb
    db_session_mock.add.assert_not_called()

def test_award_badge_race_condition(badge_repo, db_session_mock):
    """Test handling of concurrent insert race condition (IntegrityError on flush)."""
    # 1st query returns None. When we flush, it throws IntegrityError. 
    # 2nd query (in exception block) returns the suddenly-existing badge.
    
    existing_sb = StudentBadge(student_id=42, badge_id=1)
    db_session_mock.query().filter().first.side_effect = [None, existing_sb]
    
    db_session_mock.flush.side_effect = IntegrityError("statement", "params", "orig")
    
    record, awarded_now = badge_repo.award_badge(student_id=42, badge_id=1, db=db_session_mock)
    
    assert awarded_now is False
    assert record == existing_sb
    db_session_mock.rollback.assert_called_once()


# ── BadgeService Tests ─────────────────────────────────────────────────────────

@patch("app.services.badge_service.StudentRepository")
def test_evaluate_district_ranking_no_student(MockStudentRepo, badge_service, db_session_mock):
    # Setup mock repo to return None
    mock_repo_instance = MockStudentRepo.return_value
    mock_repo_instance.get_student_by_id.return_value = None
    
    rank = badge_service.evaluate_district_ranking(db_session_mock, student_id=99)
    assert rank is None

@patch("app.services.badge_service.StudentRepository")
def test_evaluate_district_ranking_awards_rank_1(MockStudentRepo, badge_service, db_session_mock):
    # Setup student
    mock_student = MagicMock()
    mock_student.district_id = 5
    mock_repo_instance = MockStudentRepo.return_value
    mock_repo_instance.get_student_by_id.return_value = mock_student

    # We mock SQLAlchemy query chain values. It's complex, so we patch the higher 
    # rank query count to be 0 (meaning this student is rank 1).
    with patch.object(db_session_mock, 'query') as mock_query:
        # Mocking student XP return
        mock_scalar = MagicMock(return_value=1200)
        # Mocking count of students with MORE XP
        mock_count = MagicMock(return_value=0) # 0 people higher = Rank 1
        
        # Define chain responses
        mock_query.return_value.filter.return_value.scalar = mock_scalar
        mock_query.return_value.join.return_value.filter.return_value.group_by.return_value.having.return_value.count = mock_count
        
        # We need to test the award behavior
        mock_badge = Badge(id=77, name="Top 10 District")
        badge_service.badge_repo.get_badge_by_name = MagicMock(return_value=mock_badge)
        badge_service.badge_repo.award_badge = MagicMock()

        rank = badge_service.evaluate_district_ranking(db_session_mock, student_id=42)
        
        assert rank == 1
        badge_service.badge_repo.get_badge_by_name.assert_called_once_with("Top 10 District", db_session_mock)
        badge_service.badge_repo.award_badge.assert_called_once_with(42, 77, db_session_mock)
