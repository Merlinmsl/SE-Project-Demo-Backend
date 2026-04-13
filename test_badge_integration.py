import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.quiz_session import QuizSession
from app.schemas.quiz import QuizSubmitRequest
from app.services.quiz_service import QuizService
from app.repositories.quiz_repository import QuizRepository


@pytest.fixture
def db_session_mock():
    return MagicMock(spec=Session)

@pytest.fixture
def quiz_repo():
    return MagicMock(spec=QuizRepository)

@pytest.fixture
def quiz_service(quiz_repo):
    return QuizService(repository=quiz_repo)

@patch("app.services.quiz_service.badge_service")
def test_submit_quiz_triggers_district_badge_evaluation(mock_badge_service, quiz_service, db_session_mock):
    """
    Test that when a student successfully submits a completed quiz, 
    the district badge evaluation runs automatically to award them their Rank (MIN-62).
    """
    # 1. Setup mock quiz session
    session = QuizSession(
        id=123, 
        student_id=456, 
        subject_id=789, 
        status="in_progress",
        difficulty_profile="beginner",
        ended_at=None
    )
    # Give the repository mock logic to return our session
    quiz_service._repo.get_session.return_value = session
    quiz_service._repo.update_study_streak.return_value = 1

    # Empty payload, answers don't matter for demonstrating the mock trigger
    payload = QuizSubmitRequest(
        session_id=123,
        answers=[]
    )

    # 2. Call the submit method
    quiz_service.submit_quiz(db_session_mock, payload)
    
    # 3. Assert stats were updated and it triggered evaluation
    quiz_service._repo.update_student_stats.assert_called_once()
    mock_badge_service.evaluate_district_ranking.assert_called_once_with(db_session_mock, 456)


@patch("app.services.quiz_service.badge_service")
def test_submit_quiz_does_not_fail_if_badge_evaluation_fails(mock_badge_service, quiz_service, db_session_mock):
    """
    Ensure the core functionality of completing a quiz does not break if 
    the badge service encounters a failure/exception (Fault Tolerance).
    """
    session = QuizSession(
        id=124, student_id=457, subject_id=789, status="in_progress", difficulty_profile="advanced"
    )
    quiz_service._repo.get_session.return_value = session
    quiz_service._repo.update_study_streak.return_value = 2

    payload = QuizSubmitRequest(session_id=124, answers=[])

    # Simulate an error in rank processing 
    mock_badge_service.evaluate_district_ranking.side_effect = Exception("DB Connection Timeout in Ranking")

    # The submit should still succeed
    response = quiz_service.submit_quiz(db_session_mock, payload)
    
    # Proof: it didn't crash, and stats updated
    assert response is not None
    quiz_service._repo.update_student_stats.assert_called_once()
    quiz_service._repo.save_quiz_submission.assert_called_once()
