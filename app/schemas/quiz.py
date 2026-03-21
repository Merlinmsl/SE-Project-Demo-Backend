from pydantic import BaseModel, field_validator
from typing import Optional
from enum import Enum
from datetime import datetime


class QuizMode(str, Enum):
    topic = "topic"
    term = "term"


class DifficultyProfile(str, Enum):
    beginner = "beginner"
    low = "low"
    medium = "medium"
    high = "high"
    advanced = "advanced"


# --- Request Schemas ---

class QuizStartRequest(BaseModel):
    student_id: int
    subject_id: int
    mode: QuizMode
    topic_id: Optional[int] = None

    @field_validator("topic_id")
    @classmethod
    def validate_topic_for_mode(cls, v, info):
        mode = info.data.get("mode")
        if mode == QuizMode.topic and v is None:
            raise ValueError("topic_id is required when mode is 'topic'")
        return v


# --- Response Schemas (is_correct is NEVER exposed to students) ---

class QuizQuestionOption(BaseModel):
    id: int
    option_text: str

    class Config:
        from_attributes = True


class QuizQuestion(BaseModel):
    id: int
    question_text: str
    difficulty: str
    options: list[QuizQuestionOption]

    class Config:
        from_attributes = True


class QuizStartResponse(BaseModel):
    session_id: int
    mode: QuizMode
    difficulty_profile: DifficultyProfile
    total_questions: int
    questions: list[QuizQuestion]

class QuizSubmitAnswer(BaseModel):
    question_id: int
    selected_option_id: Optional[int] = None

class QuizSubmitRequest(BaseModel):
    session_id: int
    answers: list[QuizSubmitAnswer]

class AnswerResult(BaseModel):
    question_id: int
    is_correct: bool
    xp_earned: int
    bonus_xp: int


class QuizSubmitResponse(BaseModel):
    score_percentage: float
    xp_earned: int
    total_bonus_xp: int
    completion_bonus_xp: int
    streak_bonus_xp: int
    current_streak: int
    is_perfect_score: bool
    total_correct: int
    total_questions: int
    is_beginner: bool
    answer_results: list[AnswerResult]

