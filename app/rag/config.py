# config.py
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root
load_dotenv()

# --- Project paths ---
PROJECT_ROOT = Path(__file__).resolve().parent
RESOURCES_DIR = PROJECT_ROOT / "resources"

# --- Chroma settings ---
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "chroma_db")
CHROMA_DIR = PROJECT_ROOT / CHROMA_PERSIST_DIR
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "grade9_textbooks")

# Optional: Chroma server mode (leave empty for local)
CHROMA_HOST = os.getenv("CHROMA_HOST", "").strip()
CHROMA_PORT = os.getenv("CHROMA_PORT", "").strip()

# --- LLM provider switch ---
# "gemini" (default) or "minimax". Embeddings ALWAYS use Gemini —
# the existing Chroma index is built with Gemini embeddings, switching
# providers would invalidate it. Only the answer-generation step changes.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()

# --- Gemini (used for embeddings always, and for generation when LLM_PROVIDER=gemini) ---
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY", "") or "").strip()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-flash-latest")

# --- MiniMax (used when LLM_PROVIDER=minimax) ---
MINIMAX_API_KEY = (os.getenv("MINIMAX_API_KEY", "") or "").strip()
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1").strip()
MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7").strip()

# Embeddings
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "32"))
DOC_TASK_TYPE = os.getenv("DOC_TASK_TYPE", "RETRIEVAL_DOCUMENT")
QUERY_TASK_TYPE = os.getenv("QUERY_TASK_TYPE", "QUESTION_ANSWERING")

# Chunking
CHUNK_SIZE_CHARS = int(os.getenv("CHUNK_SIZE_CHARS", "2500"))
CHUNK_OVERLAP_CHARS = int(os.getenv("CHUNK_OVERLAP_CHARS", "400"))

# Retrieval
TOP_K = int(os.getenv("TOP_K", "8"))
MAX_DISTANCE_FOR_MATCH = float(os.getenv("MAX_DISTANCE_FOR_MATCH", "0.45"))

# Confidence thresholds (based on cosine distance)
CONFIDENCE_HIGH = 0.15      # very close match
CONFIDENCE_MEDIUM = 0.28    # decent match
# anything above MEDIUM but below MAX_DISTANCE_FOR_MATCH = low confidence

# Output
ANSWER_NOT_FOUND_TEXT = "NOT FOUND"


import warnings

def validate_rag_config() -> None:
    """Validate RAG configuration on startup. Warns instead of crashing."""
    issues = []

    if not GEMINI_API_KEY:
        issues.append("GEMINI_API_KEY is not set — embeddings (and Gemini generation) will not work")

    if LLM_PROVIDER not in {"gemini", "minimax"}:
        issues.append(f"LLM_PROVIDER='{LLM_PROVIDER}' is invalid — use 'gemini' or 'minimax'")

    if LLM_PROVIDER == "minimax" and not MINIMAX_API_KEY:
        issues.append("LLM_PROVIDER=minimax but MINIMAX_API_KEY is not set")

    if not CHROMA_HOST and not CHROMA_DIR.exists():
        issues.append(f"Chroma directory '{CHROMA_DIR}' does not exist — run build_index first")

    if CHUNK_SIZE_CHARS < 500:
        issues.append(f"CHUNK_SIZE_CHARS={CHUNK_SIZE_CHARS} is too small (min 500)")

    if CHUNK_OVERLAP_CHARS >= CHUNK_SIZE_CHARS:
        issues.append("CHUNK_OVERLAP_CHARS must be less than CHUNK_SIZE_CHARS")

    if MAX_DISTANCE_FOR_MATCH <= 0 or MAX_DISTANCE_FOR_MATCH > 1:
        issues.append(f"MAX_DISTANCE_FOR_MATCH={MAX_DISTANCE_FOR_MATCH} should be between 0 and 1")

    for issue in issues:
        warnings.warn(f"[RAG CONFIG] {issue}", stacklevel=2)

    return len(issues) == 0


# Run validation on import
validate_rag_config()
