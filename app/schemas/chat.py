from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    subject: Optional[str] = None
    topic_id: Optional[int] = None
    session_id: Optional[str] = Field(default=None, max_length=64)


class ChatSource(BaseModel):
    source_file: str
    subject: str
    page_start: str
    page_end: str
    pages: List[int] = []
    citation: str = ""
    distance: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
    cited_pages: List[int] = []
    confidence: str = "none"
    is_on_topic: bool = True
    matched: bool
    session_id: str


class ChatSessionOut(BaseModel):
    session_id: str
    title: str
    first_question: str
    message_count: int
    subject: Optional[str] = None
    started_at: datetime
    last_message_at: datetime


class ChatHistoryItem(BaseModel):
    id: int
    question: str
    answer: str
    subject: Optional[str] = None
    topic: Optional[str] = None
    matched: bool
    created_at: datetime

    class Config:
        from_attributes = True
