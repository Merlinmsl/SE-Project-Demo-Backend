from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.subject import Subject
from app.schemas.chat import ChatRequest, ChatResponse
from app.rag.chat_service import chat_service

router = APIRouter(prefix="/chat", tags=["Student - AI Chat"])


@router.get("/subjects")
def list_chat_subjects(db: Session = Depends(get_db)):
    """Return all subjects available for AI chat."""
    subjects = db.query(Subject.name).distinct().all()
    return [s[0] for s in subjects]


@router.post("/ask", response_model=ChatResponse)
def ask_question(data: ChatRequest, db: Session = Depends(get_db)):
    """
    Ask the AI tutor a question.
    Optionally pass a subject name to filter answers to that subject only.
    """
    if not data.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Validate subject exists if provided
    if data.subject:
        exists = db.query(Subject).filter(Subject.name == data.subject).first()
        if not exists:
            raise HTTPException(status_code=400, detail=f"Subject '{data.subject}' not found")

    result = chat_service.ask(
        question=data.question.strip(),
        subject=data.subject,
    )

    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
        matched=result["matched"],
    )
