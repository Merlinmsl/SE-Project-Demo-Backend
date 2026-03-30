from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.subject import Subject
from app.models.topic import Topic
from app.models.ai_chat_log import AiChatLog
from app.schemas.chat import ChatRequest, ChatResponse
from app.rag.chat_service import chat_service
from app.services.content_filter import validate_chat_input, check_subject_relevance

router = APIRouter(prefix="/chat", tags=["Student - AI Chat"])


@router.get("/subjects")
def list_chat_subjects(db: Session = Depends(get_db)):
    """Return all subjects available for AI chat."""
    subjects = db.query(Subject.id, Subject.name).all()
    return [{"id": s.id, "name": s.name} for s in subjects]


@router.get("/subjects/{subject_id}/topics")
def list_subject_topics(subject_id: int, db: Session = Depends(get_db)):
    """Return all topics for a subject — useful for lesson-specific chat."""
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    topics = db.query(Topic).filter(Topic.subject_id == subject_id).all()
    return [{"id": t.id, "name": t.name} for t in topics]


@router.post("/ask", response_model=ChatResponse)
def ask_question(data: ChatRequest, db: Session = Depends(get_db)):
    """
    Ask the AI tutor a lesson-related question.
    Pass subject to filter by subject, topic_id to focus on a specific lesson,
    and session_id to continue a conversation.
    """
    if not data.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Validate input before hitting the RAG pipeline
    check = validate_chat_input(data.question)
    if not check.is_valid:
        raise HTTPException(status_code=400, detail=check.reason)

    subject_name = None
    subject_id = None
    topic_name = None
    topic_id = None

    # Validate subject
    if data.subject:
        subject_obj = db.query(Subject).filter(Subject.name == data.subject).first()
        if not subject_obj:
            raise HTTPException(status_code=400, detail=f"Subject '{data.subject}' not found")
        subject_name = subject_obj.name
        subject_id = subject_obj.id

    # Validate topic and auto-resolve subject from topic
    if data.topic_id:
        topic_obj = db.query(Topic).filter(Topic.id == data.topic_id).first()
        if not topic_obj:
            raise HTTPException(status_code=400, detail="Topic not found")
        topic_name = topic_obj.name
        topic_id = topic_obj.id

        # Auto-set subject from topic if not provided
        if not subject_name:
            parent_subject = db.query(Subject).filter(Subject.id == topic_obj.subject_id).first()
            if parent_subject:
                subject_name = parent_subject.name
                subject_id = parent_subject.id

    # Check if question seems related to the selected subject
    if subject_name and not check_subject_relevance(data.question, subject_name):
        # Log the off-topic attempt
        off_topic_log = AiChatLog(
            subject_id=subject_id,
            topic_id=topic_id,
            session_id=data.session_id,
            question=data.question.strip(),
            response="[OFF-TOPIC]",
            matched=0,
            is_off_topic=1,
        )
        db.add(off_topic_log)
        db.commit()

        return ChatResponse(
            answer=f"Your question doesn't seem to be related to {subject_name}. "
                   f"Try asking something about your {subject_name} lessons, "
                   f"or switch to a different subject.",
            sources=[],
            cited_pages=[],
            confidence="none",
            matched=False,
            is_on_topic=False,
            session_id=data.session_id or "",
        )

    result = chat_service.ask(
        question=data.question.strip(),
        subject=subject_name,
        topic_name=topic_name,
        session_id=data.session_id,
        student_id=None,  # TODO: wire from auth
        subject_id=subject_id,
        topic_id=topic_id,
        db=db,
    )

    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
        cited_pages=result.get("cited_pages", []),
        confidence=result.get("confidence", "none"),
        matched=result["matched"],
        session_id=result["session_id"],
    )
