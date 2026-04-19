from pydantic import BaseModel
from datetime import datetime


class BadgeOut(BaseModel):
    id: int
    name: str
    description: str | None
    image_url: str | None
    category: str | None


class StudentBadgeOut(BaseModel):
    id: int
    student_id: int
    awarded_at: datetime
    badge: BadgeOut


class DistrictRankOut(BaseModel):
    rank: int | None
    district_id: int | None
    district_name: str | None
    has_badge: bool
    badge_name: str | None
"""
Badge Pydantic schemas — MIN-61

Response models used by the ``/me/badges`` endpoint and any other
route that needs to surface badge or student-badge data to the frontend.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BadgeOut(BaseModel):
    """Public representation of a badge definition row."""

    id: int
    name: str
    description: str | None = None
    image_url: str | None = None

    model_config = {"from_attributes": True}


class StudentBadgeOut(BaseModel):
    """A badge that has been awarded to a student, enriched with badge metadata.

    The ``awarded_at`` field is always present so the frontend can display
    "earned on …" alongside the badge artwork.
    """

    badge_id: int
    name: str
    description: str | None = None
    image_url: str | None = None
    awarded_at: datetime

    model_config = {"from_attributes": True}


class StudentBadgesListOut(BaseModel):
    """Top-level wrapper returned by ``GET /me/badges``.

    Wrapping the list lets us extend the response with pagination or summary
    fields (e.g. ``total_count``) in a future sprint without a breaking change.
    """

    total_count: int
    badges: list[StudentBadgeOut]
