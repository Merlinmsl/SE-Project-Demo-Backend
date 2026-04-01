from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.subject import Subject
from app.models.topic import Topic
from app.models.ai_chat_log import AiChatLog
from sqlalchemy import func
from app.schemas.chat import ChatRequest, ChatResponse, ChatSessionOut, ChatHistoryItem
from app.rag.chat_service import chat_service
from app.services.content_filter import (
    validate_chat_input,
    check_subject_relevance,
    check_harmful_content,
    check_prompt_injection,
)

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

    # Block harmful content
    safety = check_harmful_content(data.question)
    if not safety.is_valid:
        flagged_log = AiChatLog(
            session_id=data.session_id,
            question=data.question.strip(),
            response="[BLOCKED]",
            matched=0,
            is_flagged=1,
            flag_reason="harmful_content",
        )
        db.add(flagged_log)
        db.commit()
        raise HTTPException(status_code=400, detail=safety.reason)

    # Block prompt injection attempts
    injection = check_prompt_injection(data.question)
    if not injection.is_valid:
        flagged_log = AiChatLog(
            session_id=data.session_id,
            question=data.question.strip(),
            response="[BLOCKED]",
            matched=0,
            is_flagged=1,
            flag_reason="prompt_injection",
        )
        db.add(flagged_log)
        db.commit()
        raise HTTPException(status_code=400, detail=injection.reason)

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


@router.get("/sessions", response_model=list[ChatSessionOut])
def list_chat_sessions(db: Session = Depends(get_db)):
    """List all chat sessions grouped by session_id."""
    rows = (
        db.query(
            AiChatLog.session_id,
            func.min(AiChatLog.question).label("first_question"),
            func.count(AiChatLog.id).label("message_count"),
            func.min(AiChatLog.created_at).label("started_at"),
            func.max(AiChatLog.created_at).label("last_message_at"),
        )
        .filter(AiChatLog.session_id.isnot(None))
        .group_by(AiChatLog.session_id)
        .order_by(func.max(AiChatLog.created_at).desc())
        .all()
    )

    return [
        ChatSessionOut(
            session_id=r.session_id,
            first_question=r.first_question or "",
            message_count=r.message_count,
            started_at=r.started_at,
            last_message_at=r.last_message_at,
        )
        for r in rows
    ]


@router.get("/sessions/{session_id}", response_model=list[ChatHistoryItem])
def get_session_history(session_id: str, db: Session = Depends(get_db)):
    """Get full conversation history for a specific chat session."""
    logs = (
        db.query(AiChatLog, Subject.name)
        .outerjoin(Subject, Subject.id == AiChatLog.subject_id)
        .filter(AiChatLog.session_id == session_id)
        .order_by(AiChatLog.created_at.asc())
        .all()
    )

    if not logs:
        raise HTTPException(status_code=404, detail="Session not found")

    return [
        ChatHistoryItem(
            id=log.id,
            question=log.question or "",
            answer=log.response or "",
            subject=subj_name,
            matched=bool(log.matched),
            created_at=log.created_at,
        )
        for log, subj_name in logs
    ]


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete all messages in a chat session."""
    count = (
        db.query(AiChatLog)
        .filter(AiChatLog.session_id == session_id)
        .delete()
    )

    if count == 0:
        raise HTTPException(status_code=404, detail="Session not found")

    db.commit()
    return {"ok": True, "deleted": count}
