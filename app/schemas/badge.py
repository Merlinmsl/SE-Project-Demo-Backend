from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class BadgeOut(BaseModel):
    """Public representation of a badge definition row."""
    id: int
    name: str
    description: str | None = None
    image_url: str | None = None
    category: str | None = None

    model_config = {"from_attributes": True}


class StudentBadgeOut(BaseModel):
    """A badge that has been awarded to a student, enriched with badge metadata."""
    id: int
    student_id: int
    awarded_at: datetime
    badge: BadgeOut

    model_config = {"from_attributes": True}


class StudentBadgesListOut(BaseModel):
    """Top-level wrapper returned by GET /me/badges."""
    total_count: int
    badges: list[StudentBadgeOut]


class DistrictRankOut(BaseModel):
    rank: int | None
    district_id: int | None
    district_name: str | None
    has_badge: bool
    badge_name: str | None
