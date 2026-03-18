from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.quiz import QuizStartRequest, QuizStartResponse, QuizSubmitRequest, QuizSubmitResponse
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


@router.post("/submit", response_model=QuizSubmitResponse, status_code=200)
def submit_quiz(data: QuizSubmitRequest, db: Session = Depends(get_db)):
    """
    Submit answers for evaluation and end active quiz session.
    """
    return quiz_service.submit_quiz(db, data)


@router.get("/topics", status_code=200)
def get_topics(subject_id: int, db: Session = Depends(get_db)):
    """
    Fetch all topics for a given subject.
    """
    from app.models.topic import Topic
    topics = db.query(Topic).filter(Topic.subject_id == subject_id).all()
    return [{"id": t.id, "name": t.name} for t in topics]