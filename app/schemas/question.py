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

# --- Bonus XP for getting every question right in a quiz ---
PERFECT_SCORE_BONUS = 50

# --- Streak bonus XP (awarded when student has consecutive-day activity) ---
STREAK_BONUS_THRESHOLDS = [
    (3,  10),   # 3-day streak  → 10 bonus XP
    (7,  25),   # 7-day streak  → 25 bonus XP
    (14, 50),   # 14-day streak → 50 bonus XP
    (30, 100),  # 30-day streak → 100 bonus XP
]


def get_streak_bonus(current_streak: int) -> int:
    """Return bonus XP for the given streak length."""
    bonus = 0
    for min_days, xp in STREAK_BONUS_THRESHOLDS:
        if current_streak >= min_days:
            bonus = xp
    return bonus

# --- Student leveling thresholds ---
# Each tuple is (min_xp, level_number, level_name)
LEVEL_THRESHOLDS = [
    (0,     1,  "Beginner"),
    (100,   2,  "Learner"),
    (300,   3,  "Explorer"),
    (600,   4,  "Achiever"),
    (1000,  5,  "Scholar"),
    (1500,  6,  "Expert"),
    (2200,  7,  "Master"),
    (3000,  8,  "Champion"),
    (4000,  9,  "Legend"),
    (5500,  10, "Grandmaster"),
]


def get_level_for_xp(total_xp: int) -> dict:
    """Return current level info and progress to next level."""
    current = LEVEL_THRESHOLDS[0]
    for threshold in LEVEL_THRESHOLDS:
        if total_xp >= threshold[0]:
            current = threshold
        else:
            break

    current_min, level, name = current

    # Find next level threshold
    idx = LEVEL_THRESHOLDS.index(current)
    if idx + 1 < len(LEVEL_THRESHOLDS):
        next_min = LEVEL_THRESHOLDS[idx + 1][0]
        xp_to_next = next_min - total_xp
        progress = ((total_xp - current_min) / (next_min - current_min)) * 100
    else:
        # Max level
        next_min = None
        xp_to_next = 0
        progress = 100.0

    return {
        "level": level,
        "level_name": name,
        "xp_to_next_level": max(xp_to_next, 0),
        "progress_percentage": round(min(progress, 100.0), 1),
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

    @field_validator("xp_value", mode="before")
    @classmethod
    def validate_xp_value(cls, v):
        if v is None:
            return None
        if isinstance(v, int) and v <= 0:
            return None  # treat 0 or negative as "use default"
        return v

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
