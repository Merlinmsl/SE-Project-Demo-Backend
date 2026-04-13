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
