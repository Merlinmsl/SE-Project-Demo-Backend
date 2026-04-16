from pydantic import BaseModel
from typing import Optional
from datetime import date

class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    last_completed_date: Optional[date] = None

class StreakCompleteResponse(BaseModel):
    status: str
    message: str
    current_streak: int
    longest_streak: int

class StreakHistoryItem(BaseModel):
    completed_date: date
    tasks_completed: Optional[dict] = None
