from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import chromadb

from app.rag.config import (
    CHROMA_DIR,
    CHROMA_HOST,
    CHROMA_PORT,
    COLLECTION_NAME,
    TOP_K,
    MAX_DISTANCE_FOR_MATCH,
)


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    metadata: Dict[str, Any]
    distance: float


class ChromaVectorStore:
    def __init__(self) -> None:
        if CHROMA_HOST and CHROMA_PORT:
            self.client = chromadb.HttpClient(host=CHROMA_HOST, port=int(CHROMA_PORT))
        else:
            self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))

        try:
            self.collection = self.client.get_collection(name=COLLECTION_NAME)
        except Exception:
            self.collection = self.client.create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )

    def count(self) -> int:
        return self.collection.count()

    def upsert(
        self,
        *,
        ids: List[str],
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> None:
        if not (len(ids) == len(texts) == len(metadatas) == len(embeddings)):
            raise ValueError("ids/texts/metadatas/embeddings length mismatch")
        self.collection.upsert(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)

    def query(
        self,
        *,
        query_embedding: List[float],
        n_results: int = TOP_K,
        subject_filter: Optional[str] = None,
    ) -> Tuple[Optional[RetrievedChunk], List[RetrievedChunk]]:
        where = {"subject": subject_filter} if subject_filter else None

        res = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]

        hits: List[RetrievedChunk] = []
        for doc, meta, dist in zip(docs, metas, dists):
            if doc is None or meta is None or dist is None:
                continue
            hits.append(RetrievedChunk(text=str(doc), metadata=dict(meta), distance=float(dist)))

        best = hits[0] if hits else None
        return best, hits

    def is_match(self, best: Optional[RetrievedChunk]) -> bool:
        if best is None:
            return False
        return best.distance <= MAX_DISTANCE_FOR_MATCH
