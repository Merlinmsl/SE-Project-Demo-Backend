from __future__ import annotations

import re
import uuid
from typing import List, Optional, Set

from google import genai
from google.genai import types
from sqlalchemy.orm import Session as DBSession

from app.rag.config import GEMINI_API_KEY, LLM_MODEL, ANSWER_NOT_FOUND_TEXT, TOP_K
from app.rag.embedding import GeminiEmbedder
from app.rag.vectorstore import ChromaVectorStore, RetrievedChunk
from app.models.ai_chat_log import AiChatLog


def _build_context(hits: List[RetrievedChunk], max_chunks: int = 6) -> str:
    blocks = []
    for i, h in enumerate(hits[:max_chunks], start=1):
        sf = h.metadata.get("source_file", "unknown")
        subj = h.metadata.get("subject", "unknown")
        pages_csv = h.metadata.get("pages", "")
        ps = h.metadata.get("page_start", "?")
        pe = h.metadata.get("page_end", "?")

        # Prefer the precise page list; fall back to range
        if pages_csv:
            page_label = f"pages {pages_csv}"
        else:
            page_label = f"pages {ps}-{pe}"

        blocks.append(
            f"[SOURCE {i}] subject={subj} file={sf} {page_label}\n{h.text}"
        )
    return "\n\n".join(blocks)


def _format_sources(hits: List[RetrievedChunk]) -> list[dict]:
    sources = []
    for h in hits[:5]:
        pages_csv = h.metadata.get("pages", "")
        page_ints = [int(p) for p in pages_csv.split(",") if p.strip().isdigit()] if pages_csv else []
        sources.append({
            "source_file": h.metadata.get("source_file", "unknown"),
            "subject": h.metadata.get("subject", "unknown"),
            "page_start": h.metadata.get("page_start", "?"),
            "page_end": h.metadata.get("page_end", "?"),
            "pages": page_ints,
            "distance": round(h.distance, 4),
        })
    return sources


def _extract_cited_pages(answer: str) -> List[int]:
    """Pull every page number the LLM cited via (Page X) or (Pages X, Y)."""
    found: Set[int] = set()
    # match patterns like (Page 12) or (Pages 12, 14, 15)
    for m in re.finditer(r"\(pages?\s+([\d,\s]+)\)", answer, re.IGNORECASE):
        for num in re.findall(r"\d+", m.group(1)):
            found.add(int(num))
    return sorted(found)


def _build_history_context(history: list[AiChatLog], max_turns: int = 4) -> str:
    """Format recent conversation history for the LLM."""
    if not history:
        return ""
    lines = []
    for log in history[-max_turns:]:
        lines.append(f"Student: {log.question}")
        lines.append(f"Tutor: {log.response}")
    return "\n".join(lines)


class ChatService:
    def __init__(self) -> None:
        self.store = ChromaVectorStore()
        self.embedder = GeminiEmbedder()
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def _get_session_history(self, db: DBSession, session_id: str) -> list[AiChatLog]:
        """Fetch recent conversation history for a chat session."""
        return (
            db.query(AiChatLog)
            .filter(AiChatLog.session_id == session_id)
            .order_by(AiChatLog.created_at.asc())
            .limit(10)
            .all()
        )

    def ask(
        self,
        question: str,
        subject: Optional[str] = None,
        topic_name: Optional[str] = None,
        session_id: Optional[str] = None,
        student_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        topic_id: Optional[int] = None,
        db: Optional[DBSession] = None,
    ) -> dict:
        """Answer a student question using RAG with conversation history."""

        # Generate or reuse session id for conversation continuity
        if not session_id:
            session_id = uuid.uuid4().hex[:16]

        # Load conversation history if session exists
        history_text = ""
        if db and session_id:
            history = self._get_session_history(db, session_id)
            history_text = _build_history_context(history)

        q_vec = self.embedder.embed_query(question)

        best, hits = self.store.query(
            query_embedding=q_vec,
            n_results=TOP_K,
            subject_filter=subject,
        )

        # If no close match found, return not found
        if not self.store.is_match(best):
            # Save to chat log even when not matched
            if db and student_id:
                self._save_log(db, student_id, subject_id, topic_id, session_id, question, ANSWER_NOT_FOUND_TEXT, matched=False)

            return {
                "answer": ANSWER_NOT_FOUND_TEXT,
                "sources": [],
                "cited_pages": [],
                "matched": False,
                "session_id": session_id,
            }

        context = _build_context(hits)

        # Build topic-aware system prompt
        topic_hint = ""
        if topic_name:
            topic_hint = f"\n- The student is currently studying the topic: '{topic_name}'. Tailor your answer to this lesson."

        system_instruction = f"""
You are a tutor chatbot for Sri Lankan students.
STRICT RULES:
- Use ONLY the provided CONTEXT. Do not use outside knowledge.
- If the answer is not clearly present in CONTEXT, output exactly: {ANSWER_NOT_FOUND_TEXT}
- Keep answers simple, correct, and step-by-step.
- Be encouraging and helpful.
- ALWAYS cite the exact page number(s) where you found the answer. Use the format (Page X) or (Pages X, Y) inline in your response. The page numbers are provided in each SOURCE header.{topic_hint}
""".strip()

        # Build message with history for follow-up questions
        parts = []
        if history_text:
            parts.append(f"CONVERSATION HISTORY:\n{history_text}")
        parts.append(f"CONTEXT:\n{context}")
        parts.append(f"QUESTION:\n{question}")
        user_message = "\n\n".join(parts)

        resp = self.client.models.generate_content(
            model=LLM_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
                max_output_tokens=800,
            ),
        )

        text = (resp.text or "").strip()
        if not text:
            text = ANSWER_NOT_FOUND_TEXT

        matched = text != ANSWER_NOT_FOUND_TEXT

        # Save to chat log
        if db and student_id:
            self._save_log(db, student_id, subject_id, topic_id, session_id, question, text, matched=matched)

        cited = _extract_cited_pages(text) if matched else []

        return {
            "answer": text,
            "sources": _format_sources(hits) if matched else [],
            "cited_pages": cited,
            "matched": matched,
            "session_id": session_id,
        }

    def _save_log(
        self, db: DBSession, student_id: int, subject_id: Optional[int],
        topic_id: Optional[int], session_id: str, question: str,
        response: str, matched: bool,
    ) -> None:
        log = AiChatLog(
            student_id=student_id,
            subject_id=subject_id,
            topic_id=topic_id,
            session_id=session_id,
            question=question,
            response=response,
            matched=1 if matched else 0,
        )
        db.add(log)
        db.commit()


# Singleton
chat_service = ChatService()
