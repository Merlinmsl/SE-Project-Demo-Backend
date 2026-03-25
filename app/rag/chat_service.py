from __future__ import annotations

from typing import List, Optional

from google import genai
from google.genai import types

from app.rag.config import GEMINI_API_KEY, LLM_MODEL, ANSWER_NOT_FOUND_TEXT, TOP_K
from app.rag.embedding import GeminiEmbedder
from app.rag.vectorstore import ChromaVectorStore, RetrievedChunk


def _build_context(hits: List[RetrievedChunk], max_chunks: int = 6) -> str:
    blocks = []
    for i, h in enumerate(hits[:max_chunks], start=1):
        sf = h.metadata.get("source_file", "unknown")
        subj = h.metadata.get("subject", "unknown")
        ps = h.metadata.get("page_start", "?")
        pe = h.metadata.get("page_end", "?")
        blocks.append(f"[SOURCE {i}] subject={subj} file={sf} pages={ps}-{pe}\n{h.text}")
    return "\n\n".join(blocks)


def _format_sources(hits: List[RetrievedChunk]) -> list[dict]:
    sources = []
    for h in hits[:5]:
        sources.append({
            "source_file": h.metadata.get("source_file", "unknown"),
            "subject": h.metadata.get("subject", "unknown"),
            "page_start": h.metadata.get("page_start", "?"),
            "page_end": h.metadata.get("page_end", "?"),
            "distance": round(h.distance, 4),
        })
    return sources


class ChatService:
    def __init__(self) -> None:
        self.store = ChromaVectorStore()
        self.embedder = GeminiEmbedder()
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def ask(self, question: str, subject: Optional[str] = None) -> dict:
        """Answer a student question using RAG with optional subject filter."""
        q_vec = self.embedder.embed_query(question)

        best, hits = self.store.query(
            query_embedding=q_vec,
            n_results=TOP_K,
            subject_filter=subject,
        )

        # If no close match found, return not found
        if not self.store.is_match(best):
            return {
                "answer": ANSWER_NOT_FOUND_TEXT,
                "sources": [],
                "matched": False,
            }

        context = _build_context(hits)

        system_instruction = """
You are a tutor chatbot for Sri Lankan students.
STRICT RULES:
- Use ONLY the provided CONTEXT. Do not use outside knowledge.
- If the answer is not clearly present in CONTEXT, output exactly: NOT FOUND
- Keep answers simple, correct, and step-by-step.
- Be encouraging and helpful.
""".strip()

        user_message = f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"

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

        return {
            "answer": text,
            "sources": _format_sources(hits) if matched else [],
            "matched": matched,
        }


# Singleton
chat_service = ChatService()
