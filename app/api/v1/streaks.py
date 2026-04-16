from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.security import AuthUser
from app.db.session import get_db
from app.repositories.student_repo import StudentRepository
from app.schemas.streak import StreakResponse, StreakCompleteResponse, StreakHistoryItem
from app.services.streak_service import StreakService

router = APIRouter(prefix="/streaks", tags=["Student - Streaks"])

@router.get("/current", response_model=StreakResponse, status_code=200)
def get_current_streak(db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    """
    Returns current_streak, longest_streak, last_completed_date for the authenticated student.
    """
    st_repo = StudentRepository(db)
    student = st_repo.create_if_missing(user)
    
    return StreakService.get_current_streak(db, student.id)

@router.post("/complete", response_model=StreakCompleteResponse, status_code=201)
def complete_daily_streak(tasks: dict = None, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    """
    Called when student completes daily tasks; runs streak calculation logic idempotently.
    """
    st_repo = StudentRepository(db)
    student = st_repo.create_if_missing(user)
    
    return StreakService.complete_daily_tasks(db, student.id, tasks)

@router.get("/history", response_model=List[StreakHistoryItem], status_code=200)
def get_streak_history(db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    """
    Returns list of completion dates for calendar/history views.
    """
    st_repo = StudentRepository(db)
    student = st_repo.create_if_missing(user)
    
    completions = StreakService.get_history(db, student.id)
    return [
        StreakHistoryItem(
            completed_date=c.completed_date,
            tasks_completed=c.tasks_completed
        ) for c in completions
    ]
