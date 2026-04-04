from __future__ import annotations

import hashlib
import re
import time
import uuid
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Set, Tuple

from google import genai
from google.genai import types
from sqlalchemy.orm import Session as DBSession

from app.rag.config import (
    GEMINI_API_KEY, LLM_MODEL, ANSWER_NOT_FOUND_TEXT, TOP_K,
    CONFIDENCE_HIGH, CONFIDENCE_MEDIUM,
)
from app.rag.embedding import GeminiEmbedder
from app.rag.vectorstore import ChromaVectorStore, RetrievedChunk
from app.models.ai_chat_log import AiChatLog
from app.services.content_filter import sanitize_llm_output


class QueryCache:
    """Simple in-memory LRU cache for RAG query results (15-minute TTL)."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 900):
        self._cache: OrderedDict[str, Tuple[float, Any]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds

    def _make_key(self, question: str, subject: Optional[str], topic: Optional[str]) -> str:
        raw = f"{question.lower().strip()}|{subject or ''}|{topic or ''}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, question: str, subject: Optional[str] = None, topic: Optional[str] = None) -> Optional[dict]:
        key = self._make_key(question, subject, topic)
        if key not in self._cache:
            return None
        ts, result = self._cache[key]
        if time.time() - ts > self._ttl:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return result

    def put(self, question: str, subject: Optional[str], topic: Optional[str], result: dict) -> None:
        key = self._make_key(question, subject, topic)
        self._cache[key] = (time.time(), result)
        self._cache.move_to_end(key)
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)


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
    """Build deduplicated, relevance-sorted source list from retrieved chunks."""
    seen: Set[str] = set()
    sources = []
    for h in sorted(hits, key=lambda x: x.distance)[:8]:
        sf = h.metadata.get("source_file", "unknown")
        ps = str(h.metadata.get("page_start", "?"))
        pe = str(h.metadata.get("page_end", "?"))
        dedup_key = f"{sf}:{ps}-{pe}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        pages_csv = h.metadata.get("pages", "")
        page_ints = [int(p) for p in pages_csv.split(",") if p.strip().isdigit()] if pages_csv else []
        subj = h.metadata.get("subject", "unknown")

        # Build human-readable citation e.g. "Science — science-g9.pdf, Page 47"
        if page_ints:
            page_label = f"Page {page_ints[0]}" if len(page_ints) == 1 else f"Pages {', '.join(str(p) for p in page_ints)}"
        else:
            page_label = f"Pages {ps}-{pe}"
        citation = f"{subj.title()} — {sf}, {page_label}"

        sources.append({
            "source_file": sf,
            "subject": subj,
            "page_start": ps,
            "page_end": pe,
            "pages": page_ints,
            "citation": citation,
            "distance": round(h.distance, 4),
        })
    return sources[:5]


def _extract_cited_pages(answer: str) -> List[int]:
    """Pull every page number the LLM cited via (Page X) or (Pages X, Y)."""
    found: Set[int] = set()
    # match patterns like (Page 12) or (Pages 12, 14, 15)
    for m in re.finditer(r"\(pages?\s+([\d,\s]+)\)", answer, re.IGNORECASE):
        for num in re.findall(r"\d+", m.group(1)):
            found.add(int(num))
    return sorted(found)


def _compute_confidence(distance: float) -> str:
    """Return a confidence label based on cosine distance of best match."""
    if distance <= CONFIDENCE_HIGH:
        return "high"
    if distance <= CONFIDENCE_MEDIUM:
        return "medium"
    return "low"


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
        self._cache = QueryCache()

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

        # Check cache for repeated questions (skip if conversation has history)
        cached = self._cache.get(question, subject, topic_name)
        if cached and not session_id:
            cached["session_id"] = session_id
            return cached

        # Load conversation history if session exists
        history_text = ""
        if db and session_id:
            history = self._get_session_history(db, session_id)
            history_text = _build_history_context(history)

        # Check if vectorstore has any indexed content
        if self.store.count() == 0:
            return {
                "answer": "No textbooks have been indexed yet. Please ask your teacher to upload study materials.",
                "sources": [],
                "cited_pages": [],
                "confidence": "none",
                "matched": False,
                "session_id": session_id,
            }

        q_vec = self.embedder.embed_query(question)

        best, hits = self.store.query(
            query_embedding=q_vec,
            n_results=TOP_K,
            subject_filter=subject,
            topic_filter=topic_name,
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
                "confidence": "none",
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

        try:
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
        except Exception as e:
            # Graceful fallback if Gemini is slow, down, or errors out
            text = (
                "Sorry, I'm having trouble generating an answer right now. "
                "Please try again in a moment."
            )

        # Sanitize LLM output for harmful content
        text = sanitize_llm_output(text)

        matched = text != ANSWER_NOT_FOUND_TEXT

        # Save to chat log
        if db and student_id:
            self._save_log(db, student_id, subject_id, topic_id, session_id, question, text, matched=matched)

        cited = _extract_cited_pages(text) if matched else []
        confidence = _compute_confidence(best.distance) if matched and best else "none"

        # Add a disclaimer for low confidence answers
        if matched and confidence == "low":
            text = (
                text
                + "\n\n---\n"
                + "Note: I'm not fully confident in this answer. "
                + "Please double-check your textbook for accuracy."
            )

        result = {
            "answer": text,
            "sources": _format_sources(hits) if matched else [],
            "cited_pages": cited,
            "confidence": confidence,
            "matched": matched,
            "session_id": session_id,
        }

        # Cache the result for repeated queries
        if matched:
            self._cache.put(question, subject, topic_name, result)

        return result

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
