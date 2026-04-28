"""
streaks.py — API endpoints for Daily Streak Tracking (MIN-290).

Endpoints:
    GET  /api/v1/streaks/current   → current + longest streak
    POST /api/v1/streaks/complete  → mark today as done, update streak
    GET  /api/v1/streaks/history   → calendar / audit list
"""

import logging
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.security import AuthUser
from app.db.session import get_db
from app.repositories.student_repo import StudentRepository
from app.schemas.streak import (
    CompleteRequest,
    StreakCompleteResponse,
    StreakHistoryItem,
    StreakResponse,
)
from app.services.streak_service import StreakService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/streaks", tags=["Student - Streaks"])


@router.get(
    "/current",
    response_model=StreakResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the authenticated student's current streak",
)
def get_current_streak(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """
    Returns **current_streak**, **longest_streak**, and **last_completed_date**
    for the authenticated student.

    - If the student has never completed a task the values are all zero / null.
    - Dates are always expressed in **UTC**.
    - Returns zeroes gracefully even if no streak record exists yet.
    """
    try:
        st_repo = StudentRepository(db)
        student = st_repo.create_if_missing(user)
        result = StreakService.get_current_streak(db, student.id)
        logger.info(
            "GET /streaks/current → user=%s student_id=%s streak=%s",
            user.clerk_user_id,
            student.id,
            result.get("current_streak"),
        )
        return result
    except Exception as exc:
        logger.error("GET /streaks/current failed for user=%s: %s", user.clerk_user_id, exc)
        # Return safe default so the dashboard still renders
        return {"current_streak": 0, "longest_streak": 0, "last_completed_date": None}


@router.post(
    "/complete",
    response_model=StreakCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark today's tasks as completed and recalculate the streak",
)
def complete_daily_streak(
    body: CompleteRequest = Body(default=CompleteRequest()),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """
    Called when a student finishes their daily tasks.

    **Streak logic (UTC day boundaries):**

    | Scenario | Condition | Action |
    |---|---|---|
    | Streak continues | last_completed_date = yesterday | current_streak += 1 |
    | Already counted | last_completed_date = today | Do nothing (idempotent) |
    | Streak broken | last_completed_date >= 2 days ago | Reset current_streak to 1 |
    | First-time user | No streak record | Create record, streak = 1 |
    """
    st_repo = StudentRepository(db)
    student = st_repo.create_if_missing(user)
    
    try:
        result = StreakService.complete_daily_tasks(db, student.id, body.tasks)
    except Exception as e:
        # Use logger so the traceback goes through the normal logging
        # pipeline (rotating files, Sentry, etc.) instead of stdout prints.
        logger.exception(
            "POST /streaks/complete failed for student_id=%s: %s",
            student.id,
            e,
        )
        # Don't leak the raw exception message to the client — it may contain
        # stacktrace hints or internal identifiers.
        raise HTTPException(status_code=500, detail="Failed to update streak")
        
    logger.info(
        "POST /streaks/complete → user=%s student_id=%s status=%s new_streak=%s",
        user.clerk_user_id,
        student.id,
        result.get("status"),
        result.get("current_streak"),
    )
    return result


@router.get(
    "/history",
    response_model=List[StreakHistoryItem],
    status_code=status.HTTP_200_OK,
    summary="Get the student's full completion history",
)
def get_streak_history(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """
    Returns a list of every day the student completed their tasks,
    ordered newest-first. Useful for rendering a calendar heat-map on
    the frontend.
    """
    st_repo = StudentRepository(db)
    student = st_repo.create_if_missing(user)

    completions = StreakService.get_history(db, student.id)
    return [
        StreakHistoryItem(
            completed_date=c.completed_date,
            tasks_completed=getattr(c, "tasks_completed", None),
        )
        for c in completions
    ]
