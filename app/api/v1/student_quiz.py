from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from pydantic import BaseModel
from typing import Optional
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


# ─── Response schemas for quiz review ───────────────────────────────────────

class ReviewOptionOut(BaseModel):
    id: int
    option_text: str
    is_correct: bool

class ReviewQuestionOut(BaseModel):
    id: int
    question_text: str
    difficulty: str
    xp_value: int
    options: list[ReviewOptionOut]

class ReviewAnswerOut(BaseModel):
    question_id: int
    selected_option_id: Optional[int]
    is_correct: bool
    correct_option_id: int

class QuizSessionReviewOut(BaseModel):
    session_id: int
    score_percentage: float
    total_correct: int
    total_questions: int
    xp_earned: int
    questions: list[ReviewQuestionOut]
    results: list[ReviewAnswerOut]


@router.get("/session/{session_id}/review", response_model=QuizSessionReviewOut, status_code=200)
def get_quiz_session_review(session_id: int, db: Session = Depends(get_db)):
    """
    Retrieve the full review data for a completed quiz session.
    Returns all questions (with options including is_correct) plus stored student answers.
    Used by the dashboard to let students re-view past quiz results.
    """
    from app.models.quiz_session import QuizSession
    from app.models.quiz_attempt import QuizAttempt
    from app.models.quiz_answer import QuizAnswer
    from app.models.question import Question, QuestionOption

    # 1. Load session
    session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Quiz session not found")
    if session.status != "completed":
        raise HTTPException(status_code=400, detail="Quiz session is not yet completed")

    # 2. Load attempt (score, xp etc.)
    attempt = db.query(QuizAttempt).filter(QuizAttempt.quiz_session_id == session_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Quiz attempt record not found")

    # 3. Load stored answers
    answers = (
        db.query(QuizAnswer)
        .filter(QuizAnswer.quiz_session_id == session_id)
        .all()
    )
    answer_map = {a.question_id: a for a in answers}

    # 4. Load questions with options (via session questions link)
    from app.models.quiz_session import QuizSessionQuestion
    q_ids_rows = db.query(QuizSessionQuestion.question_id).filter(
        QuizSessionQuestion.quiz_session_id == session_id
    ).all()
    q_ids = [r[0] for r in q_ids_rows]

    questions = (
        db.query(Question)
        .options(selectinload(Question.options))
        .filter(Question.id.in_(q_ids))
        .all()
    )

    # 5. Build response
    review_questions = []
    results = []
    for q in questions:
        opts_out = [
            ReviewOptionOut(id=opt.id, option_text=opt.option_text, is_correct=opt.is_correct)
            for opt in q.options
        ]
        review_questions.append(ReviewQuestionOut(
            id=q.id,
            question_text=q.question_text,
            difficulty=q.difficulty,
            xp_value=q.xp_value,
            options=opts_out,
        ))

        ans = answer_map.get(q.id)
        correct_opt = next((opt.id for opt in q.options if opt.is_correct), 0)
        results.append(ReviewAnswerOut(
            question_id=q.id,
            selected_option_id=ans.selected_option_id if ans else None,
            is_correct=ans.is_correct if ans is not None else False,
            correct_option_id=correct_opt,
        ))

    return QuizSessionReviewOut(
        session_id=session_id,
        score_percentage=float(attempt.score_percentage) if attempt.score_percentage else 0.0,
        total_correct=attempt.total_correct or 0,
        total_questions=attempt.total_questions or 0,
        xp_earned=attempt.xp_earned or 0,
        questions=review_questions,
        results=results,
    )
