from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime

from app.db.session import get_db
from app.core.dependencies import require_admin_api_key
from app.models.ai_chat_log import AiChatLog
from app.models.subject import Subject

router = APIRouter()


class FlaggedChatOut(BaseModel):
    id: int
    question: str
    subject_name: Optional[str] = None
    session_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FlaggedChatStatsOut(BaseModel):
    total_off_topic: int
    total_unmatched: int
    total_questions: int


@router.get(
    "/admin/chat/flagged",
    response_model=list[FlaggedChatOut],
    dependencies=[Depends(require_admin_api_key)],
)
def list_flagged_chats(
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
):
    """List recent off-topic or unmatched chat questions for admin review."""
    rows = (
        db.query(AiChatLog, Subject.name)
        .outerjoin(Subject, Subject.id == AiChatLog.subject_id)
        .filter((AiChatLog.is_off_topic == 1) | (AiChatLog.matched == 0))
        .order_by(AiChatLog.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        FlaggedChatOut(
            id=log.id,
            question=log.question or "",
            subject_name=subj_name,
            session_id=log.session_id,
            created_at=log.created_at,
        )
        for log, subj_name in rows
    ]


@router.get(
    "/admin/chat/stats",
    response_model=FlaggedChatStatsOut,
    dependencies=[Depends(require_admin_api_key)],
)
def get_chat_stats(db: Session = Depends(get_db)):
    """Return overall chat usage stats for admin dashboard."""
    total = db.query(func.count(AiChatLog.id)).scalar() or 0
    off_topic = db.query(func.count(AiChatLog.id)).filter(AiChatLog.is_off_topic == 1).scalar() or 0
    unmatched = db.query(func.count(AiChatLog.id)).filter(AiChatLog.matched == 0).scalar() or 0

    return FlaggedChatStatsOut(
        total_off_topic=off_topic,
        total_unmatched=unmatched,
        total_questions=total,
    )
