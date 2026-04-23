from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models.subject import Subject
from app.models.topic import Topic
from app.models.ai_chat_log import AiChatLog
from app.schemas.chat import ChatRequest, ChatResponse, ChatSessionOut, ChatHistoryItem
from app.rag.chat_service import chat_service
from app.services.content_filter import (
    validate_chat_input,
    check_subject_relevance,
    check_harmful_content,
    check_prompt_injection,
)
from app.services.rate_limiter import chat_rate_limiter
from app.core.security import AuthUser, ClerkJWTVerifier
from app.core.config import settings
from app.repositories.student_repo import StudentRepository

router = APIRouter(prefix="/chat", tags=["Student - AI Chat"])

_clerk_verifier: ClerkJWTVerifier | None = None


def get_optional_user(
    authorization: Optional[str] = Header(default=None),
    x_clerk_user_id: Optional[str] = Header(default=None),
    x_email: Optional[str] = Header(default=None),
) -> Optional[AuthUser]:
    """
    Like get_current_user but returns None instead of raising 401 when
    no credentials are provided.  This lets the /chat/ask endpoint work
    for both authenticated students (logs are tied to their account) and
    for unauthenticated Swagger testing (logs are saved anonymously).
    """
    # Dev mode: header bypass
    if settings.auth_mode == "dev" and x_clerk_user_id:
        return AuthUser(clerk_user_id=x_clerk_user_id, email=x_email)

    if not authorization or not authorization.lower().startswith("bearer "):
        return None  # anonymous — don't raise

    token = authorization.split(" ", 1)[1].strip()

    global _clerk_verifier
    if _clerk_verifier is None:
        _clerk_verifier = ClerkJWTVerifier(settings.clerk_jwks_url, settings.clerk_issuer)

    try:
        return _clerk_verifier.verify(token)
    except Exception:
        return None  # bad token — treat as anonymous


@router.get(
    "/subjects",
    summary="List subjects for AI chat",
    description="Returns all subjects that have indexed textbook content available for the AI tutor.",
)
def list_chat_subjects(db: Session = Depends(get_db)):
    """Return all subjects available for AI chat."""
    subjects = db.query(Subject.id, Subject.name).all()
    return [{"id": s.id, "name": s.name} for s in subjects]


@router.get(
    "/subjects/{subject_id}/topics",
    summary="List topics for a subject",
    description="Returns all topics under a subject so the student can focus the AI on a specific lesson.",
)
def list_subject_topics(subject_id: int, db: Session = Depends(get_db)):
    """Return all topics for a subject — useful for lesson-specific chat."""
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    topics = db.query(Topic).filter(Topic.subject_id == subject_id).all()
    return [{"id": t.id, "name": t.name} for t in topics]


@router.post(
    "/ask",
    response_model=ChatResponse,
    summary="Ask the AI tutor",
    description=(
        "Send a question to the RAG-based AI tutor. Optionally filter by subject/topic "
        "and continue a conversation with session_id. Includes content safety, "
        "off-topic detection, and rate limiting."
    ),
)
def ask_question(
    data: ChatRequest,
    db: Session = Depends(get_db),
    user: Optional[AuthUser] = Depends(get_optional_user),
):
    """
    Ask the AI tutor a lesson-related question.
    Pass subject to filter by subject, topic_id to focus on a specific lesson,
    and session_id to continue a conversation.
    """
    if not data.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Rate limit: 10 questions per minute per session
    rate_key = data.session_id or "anonymous"
    if not chat_rate_limiter.is_allowed(rate_key):
        raise HTTPException(
            status_code=429,
            detail="You're asking too many questions. Please wait a moment before trying again.",
        )

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
            answer=(
                f"Your question doesn't seem to be related to {subject_name}. "
                f"Try asking something about your {subject_name} lessons, "
                f"or switch to a different subject."
            ),
            sources=[],
            cited_pages=[],
            confidence="none",
            matched=False,
            is_on_topic=False,
            session_id=data.session_id or "",
        )

    # Resolve student if authenticated
    student_id = None
    if user:
        st_repo = StudentRepository(db)
        st = st_repo.create_if_missing(user)
        student_id = st.id

    result = chat_service.ask(
        question=data.question.strip(),
        subject=subject_name,
        topic_name=topic_name,
        session_id=data.session_id,
        student_id=student_id,
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


@router.get(
    "/sessions",
    response_model=list[ChatSessionOut],
    summary="List chat sessions",
    description="Returns paginated list of all chat sessions with title, message count, and timestamps.",
)
def list_chat_sessions(
    limit: int = Query(default=10, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List all chat sessions grouped by session_id with pagination."""
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
        .offset(offset)
        .limit(limit)
        .all()
    )

    def _make_title(question: str, max_len: int = 50) -> str:
        """Generate a short title from the first question."""
        q = (question or "").strip()
        if not q:
            return "Untitled chat"
        q = q.rstrip("?").strip()
        if len(q) <= max_len:
            return q
        return q[:max_len].rsplit(" ", 1)[0] + "..."

    return [
        ChatSessionOut(
            session_id=r.session_id,
            title=_make_title(r.first_question),
            first_question=r.first_question or "",
            message_count=r.message_count,
            started_at=r.started_at,
            last_message_at=r.last_message_at,
        )
        for r in rows
    ]


@router.get(
    "/sessions/{session_id}",
    response_model=list[ChatHistoryItem],
    summary="Get session history",
    description="Returns the full Q&A conversation history for a specific chat session.",
)
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


@router.delete(
    "/sessions/{session_id}",
    summary="Delete a chat session",
    description="Permanently deletes all messages in a chat session.",
)
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
