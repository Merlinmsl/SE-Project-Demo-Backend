"""
notifications.py — API endpoints for the student notification system (MIN-63 AC-3).

Endpoints:
    GET  /api/v1/notifications           → list all (or unread-only) notifications
    POST /api/v1/notifications/{id}/read → mark a single notification as read
    POST /api/v1/notifications/read-all  → mark all notifications as read
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.security import AuthUser
from app.db.session import get_db
from app.repositories.streak_repo import StreakRepository
from app.repositories.student_repo import StudentRepository
from app.schemas.streak import MarkReadResponse, NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Student - Notifications"])


@router.get(
    "",
    response_model=List[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get the authenticated student's notifications",
)
def get_notifications(
    unread_only: bool = Query(
        False,
        description="When true, only unread notifications are returned.",
    ),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """
    Returns notifications for the authenticated student, newest first.

    - Use `?unread_only=true` to fetch only unread notifications (e.g. for a badge count).
    - Notifications are created automatically by the nightly cron job when a
      streak is broken (see `cron_streak_reset.py`).
    """
    st_repo = StudentRepository(db)
    student = st_repo.create_if_missing(user)

    streak_repo = StreakRepository(db)
    notifications = streak_repo.get_notifications_by_user(student.id, unread_only=unread_only)

    return [
        NotificationResponse(
            id=n.id,
            title=n.title,
            message=n.message,
            is_read=n.is_read,
        )
        for n in notifications
    ]


@router.post(
    "/{notification_id}/read",
    response_model=MarkReadResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark a single notification as read",
)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """
    Mark a specific notification as read.

    Returns **404** if the notification does not exist or does not belong
    to the authenticated student (security guard — users cannot read each
    other's notifications).
    """
    st_repo = StudentRepository(db)
    student = st_repo.create_if_missing(user)

    streak_repo = StreakRepository(db)
    notif = streak_repo.mark_notification_read(notification_id, student.id)

    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or does not belong to this user.",
        )

    return MarkReadResponse(
        success=True,
        updated_count=1,
        message=f"Notification {notification_id} marked as read.",
    )


@router.post(
    "/read-all",
    response_model=MarkReadResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark all notifications as read",
)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """
    Mark every unread notification for the authenticated student as read.
    Returns the count of rows updated.
    """
    st_repo = StudentRepository(db)
    student = st_repo.create_if_missing(user)

    streak_repo = StreakRepository(db)
    count = streak_repo.mark_all_notifications_read(student.id)

    return MarkReadResponse(
        success=True,
        updated_count=count,
        message=f"{count} notification(s) marked as read.",
    )
