from pydantic import BaseModel, field_validator
from typing import Optional
from enum import Enum
from datetime import datetime


class DifficultyLevel(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


# --- XP Defaults ---
XP_DEFAULTS = {
    DifficultyLevel.easy: 10,
    DifficultyLevel.medium: 20,
    DifficultyLevel.hard: 30,
}

# --- Bonus XP awarded on top of base XP for harder questions ---
XP_BONUS = {
    DifficultyLevel.easy: 0,
    DifficultyLevel.medium: 5,
    DifficultyLevel.hard: 15,
}


# --- Option Schemas ---

class OptionCreate(BaseModel):
    option_text: str
    is_correct: bool = False


class OptionResponse(BaseModel):
    id: int
    option_text: str
    is_correct: bool

    class Config:
        from_attributes = True


# --- Question Schemas ---

class QuestionCreate(BaseModel):
    subject_id: int
    topic_id: int
    difficulty: DifficultyLevel
    question_text: str
    explanation: Optional[str] = None
    xp_value: Optional[int] = None
    created_by: int
    options: list[OptionCreate]

    @field_validator("options")
    @classmethod
    def validate_options(cls, v):
        if len(v) < 2:
            raise ValueError("A question must have at least 2 options")
        correct_count = sum(1 for opt in v if opt.is_correct)
        if correct_count != 1:
            raise ValueError("MCQ must have exactly 1 correct option")
        return v


class QuestionResponse(BaseModel):
    id: int
    subject_id: int
    topic_id: int
    difficulty: DifficultyLevel
    type: str
    question_text: str
    explanation: Optional[str]
    xp_value: int
    is_active: bool
    created_by: int
    created_at: datetime
    options: list[OptionResponse]

    class Config:
        from_attributes = True


class QuestionFilter(BaseModel):
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    difficulty: Optional[DifficultyLevel] = None
    is_active: Optional[bool] = None
