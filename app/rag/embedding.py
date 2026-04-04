from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

from app.rag.config import (
    GEMINI_API_KEY,
    EMBEDDING_MODEL,
    EMBED_DIM,
    EMBED_BATCH_SIZE,
    DOC_TASK_TYPE,
    QUERY_TASK_TYPE,
)


def _is_blank_key(key: str) -> bool:
    return (not key) or key.strip() == "" or key.strip() == '" "' or key.strip() == "' '" or key.strip() == " "


def _l2_normalize(vec: List[float]) -> List[float]:
    arr = np.array(vec, dtype=np.float32)
    n = np.linalg.norm(arr)
    if n == 0.0:
        return vec
    return (arr / n).astype(np.float32).tolist()


@dataclass
class GeminiEmbedder:
    api_key: str = GEMINI_API_KEY
    model: str = EMBEDDING_MODEL
    output_dim: int = EMBED_DIM
    batch_size: int = EMBED_BATCH_SIZE

    def __post_init__(self) -> None:
        if _is_blank_key(self.api_key):
            raise ValueError('GEMINI_API_KEY is blank. Put your key in .env as GEMINI_API_KEY="YOUR_KEY".')
        self.client = genai.Client(api_key=self.api_key)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts, task_type=DOC_TASK_TYPE)

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query with fast retry (3 attempts, short backoff)."""
        last_err: Optional[Exception] = None
        for attempt in range(3):
            try:
                return self._embed([text], task_type=QUERY_TASK_TYPE)[0]
            except Exception as e:
                last_err = e
                wait = 2.0 * (attempt + 1)
                logger.warning(f"Query embed attempt {attempt+1}/3 failed, retrying in {wait:.0f}s...")
                time.sleep(wait)
        raise RuntimeError(f"Query embedding failed after 3 retries: {last_err}") from last_err

    def _embed(self, texts: List[str], task_type: str) -> List[List[float]]:
        if not texts:
            return []

        out: List[List[float]] = []

        for i in range(0, len(texts), self.batch_size):
            if i > 0:
                time.sleep(4)
            batch = texts[i : i + self.batch_size]
            last_err: Optional[Exception] = None

            for attempt in range(8):
                try:
                    res = self.client.models.embed_content(
                        model=self.model,
                        contents=batch,
                        config=types.EmbedContentConfig(
                            task_type=task_type,
                            output_dimensionality=self.output_dim,
                        ),
                    )
                    embeds = res.embeddings or []
                    if len(embeds) != len(batch):
                        raise RuntimeError(f"Embedding mismatch: got {len(embeds)} for {len(batch)} inputs")

                    for e in embeds:
                        vals = list(e.values or [])
                        if self.output_dim != 3072:
                            vals = _l2_normalize(vals)
                        out.append(vals)

                    break
                except Exception as e:
                    last_err = e
                    wait = 15.0 * (2 ** attempt)
                    logger.warning(f"Rate limited, waiting {wait:.0f}s before retry {attempt+1}/8...")
                    time.sleep(wait)
            else:
                raise RuntimeError(f"Embedding failed after retries: {last_err}") from last_err

        return out
