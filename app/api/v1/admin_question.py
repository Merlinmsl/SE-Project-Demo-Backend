from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.schemas.question import (
    QuestionCreate, QuestionResponse, QuestionFilter, DifficultyLevel
)
from app.services.question_service import question_service

router = APIRouter(prefix="/admin/questions", tags=["Admin - Questions"])


@router.post("/", response_model=QuestionResponse, status_code=201)
def create_question(data: QuestionCreate, db: Session = Depends(get_db)):
    """Create a new question with MCQ options."""
    question = question_service.create_question(db, data)
    return question


@router.get("/", response_model=list[QuestionResponse])
def list_questions(
    subject_id: Optional[int] = Query(None),
    topic_id: Optional[int] = Query(None),
    difficulty: Optional[DifficultyLevel] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List questions with optional filters."""
    filters = QuestionFilter(
        subject_id=subject_id,
        topic_id=topic_id,
        difficulty=difficulty,
        is_active=is_active,
    )
    return question_service.get_questions(db, filters, skip, limit)


@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(question_id: int, db: Session = Depends(get_db)):
    """Get a single question by ID with its options."""
    return question_service.get_question_by_id(db, question_id)
