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

# --- Gemini ---
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY", "") or "").strip()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")

# Embeddings
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "32"))
DOC_TASK_TYPE = os.getenv("DOC_TASK_TYPE", "RETRIEVAL_DOCUMENT")
QUERY_TASK_TYPE = os.getenv("QUERY_TASK_TYPE", "QUESTION_ANSWERING")

# Chunking
CHUNK_SIZE_CHARS = int(os.getenv("CHUNK_SIZE_CHARS", "4500"))
CHUNK_OVERLAP_CHARS = int(os.getenv("CHUNK_OVERLAP_CHARS", "600"))

# Retrieval
TOP_K = int(os.getenv("TOP_K", "8"))
MAX_DISTANCE_FOR_MATCH = float(os.getenv("MAX_DISTANCE_FOR_MATCH", "0.30"))

# Confidence thresholds (based on cosine distance)
CONFIDENCE_HIGH = 0.12      # very close match
CONFIDENCE_MEDIUM = 0.22    # decent match
# anything above MEDIUM but below MAX_DISTANCE_FOR_MATCH = low confidence

# Output
ANSWER_NOT_FOUND_TEXT = "NOT FOUND"
