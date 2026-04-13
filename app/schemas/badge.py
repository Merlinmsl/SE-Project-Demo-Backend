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
