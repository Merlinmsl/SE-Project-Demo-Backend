"""
streak.py — Pydantic schemas for the Daily Streak Tracking feature (MIN-63).

Schemas are grouped by their purpose:
  • Request bodies  (CompleteRequest)
  • Response models (StreakResponse, StreakCompleteResponse, StreakHistoryItem)
  • Notification responses (NotificationResponse)
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class CompleteRequest(BaseModel):
    """
    Request body for POST /api/v1/streaks/complete.

    ``tasks`` is an open JSON object that the frontend can use to record
    which individual tasks contributed to today's completion — useful for
    the audit trail in daily_completions.  It is optional; omitting it is
    perfectly valid and will store an empty dict.

    Example:
        {
            "tasks": {
                "quiz_id": 42,
                "resources_viewed": 3,
                "chat_session": true
            }
        }
    """

    tasks: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional map of task identifiers / metadata completed today.",
    )


# ---------------------------------------------------------------------------
# Streak response schemas
# ---------------------------------------------------------------------------


class StreakResponse(BaseModel):
    """Returned by GET /api/v1/streaks/current."""

    model_config = ConfigDict(from_attributes=True)

    current_streak: int = Field(..., description="Consecutive days completed so far.")
    longest_streak: int = Field(..., description="All-time personal best streak.")
    last_completed_date: Optional[date] = Field(
        None, description="ISO date of the most recent completion (UTC)."
    )


class StreakCompleteResponse(BaseModel):
    """Returned by POST /api/v1/streaks/complete."""

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(
        ...,
        description=(
            "One of: 'streak_updated' (incremented or reset to 1), "
            "'already_completed' (idempotent — called again on same day)."
        ),
    )
    message: str = Field(..., description="Human-readable summary of what happened.")
    current_streak: int = Field(..., description="Streak count after this call.")
    longest_streak: int = Field(..., description="Personal best after this call.")


class StreakHistoryItem(BaseModel):
    """One entry in the list returned by GET /api/v1/streaks/history."""

    model_config = ConfigDict(from_attributes=True)

    completed_date: date = Field(..., description="The date the student was active.")
    tasks_completed: Optional[Dict[str, Any]] = Field(
        None, description="Audit metadata stored at completion time."
    )


# ---------------------------------------------------------------------------
# Notification response schemas
# ---------------------------------------------------------------------------


class NotificationResponse(BaseModel):
    """Single notification item returned by GET /api/v1/notifications."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    message: str
    is_read: bool


class MarkReadResponse(BaseModel):
    """Returned when a notification (or all notifications) are marked as read."""

    success: bool
    updated_count: int
    message: str
