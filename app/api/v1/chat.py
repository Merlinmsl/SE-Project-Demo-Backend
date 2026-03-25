from fastapi import APIRouter, HTTPException
from app.schemas.chat import ChatRequest, ChatResponse
from app.rag.chat_service import chat_service

router = APIRouter(prefix="/chat", tags=["Student - AI Chat"])


@router.post("/ask", response_model=ChatResponse)
def ask_question(data: ChatRequest):
    """
    Ask the AI tutor a question.
    Optionally pass a subject name to filter answers to that subject only.
    """
    if not data.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    result = chat_service.ask(
        question=data.question.strip(),
        subject=data.subject,
    )

    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
        matched=result["matched"],
    )
