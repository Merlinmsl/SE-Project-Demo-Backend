from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.quiz import QuizStartRequest, QuizStartResponse
from app.services.quiz_service import quiz_service

router = APIRouter(prefix="/quiz", tags=["Student - Quiz"])


@router.post("/start", response_model=QuizStartResponse, status_code=201)
def start_quiz(data: QuizStartRequest, db: Session = Depends(get_db)):
    """
    Start a new quiz for a student.

    - **mode = 'topic'**: requires topic_id, questions restricted to that topic
    - **mode = 'term'**: no topic_id needed, questions drawn from all topics (weak topics prioritized)
    """
    return quiz_service.start_quiz(db, data)
