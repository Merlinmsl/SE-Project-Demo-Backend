from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ChatRequest(BaseModel):
    question: str
    subject: Optional[str] = None
    topic_id: Optional[int] = None
    session_id: Optional[str] = None


class ChatSource(BaseModel):
    source_file: str
    subject: str
    page_start: str
    page_end: str
    pages: List[int] = []
    distance: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
    cited_pages: List[int] = []
    matched: bool
    session_id: str


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
