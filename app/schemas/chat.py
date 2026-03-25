from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    question: str
    subject: Optional[str] = None


class ChatSource(BaseModel):
    source_file: str
    subject: str
    page_start: str
    page_end: str
    distance: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
    matched: bool
