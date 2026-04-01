from __future__ import annotations

from tqdm import tqdm

from app.rag.config import RESOURCES_DIR
from app.rag.dataprocessor import list_pdfs, build_chunks_from_pdf
from app.rag.embedding import GeminiEmbedder
from app.rag.vectorstore import ChromaVectorStore


def main() -> None:
    pdfs = list_pdfs(RESOURCES_DIR)
    if not pdfs:
        print(f"No PDFs found. Put your textbooks in: {RESOURCES_DIR}")
        return

    store = ChromaVectorStore()
    embedder = GeminiEmbedder()

    total = 0

    for pdf in pdfs:
        print(f"\n--- Indexing: {pdf.name} ---")
        chunks = build_chunks_from_pdf(pdf)

        if not chunks:
            print(f"[WARN] No chunks created for {pdf.name}")
            continue

        ids = [c.chunk_id for c in chunks]
        texts = [c.text for c in chunks]
        metas = [c.metadata for c in chunks]

        # Resume support: skip chunks already in ChromaDB
        try:
            existing = store.collection.get(ids=ids, include=[])
            existing_ids = set(existing["ids"]) if existing and existing.get("ids") else set()
        except Exception:
            existing_ids = set()

        new_idx = [i for i, cid in enumerate(ids) if cid not in existing_ids]
        if not new_idx:
            print(f"All {len(chunks)} chunks already indexed, skipping.")
            total += len(chunks)
            continue

        if existing_ids:
            print(f"Resuming: {len(existing_ids)} already done, {len(new_idx)} remaining.")

        new_ids = [ids[i] for i in new_idx]
        new_texts = [texts[i] for i in new_idx]
        new_metas = [metas[i] for i in new_idx]

        embeddings: list[list[float]] = []
        for i in tqdm(range(0, len(new_texts), embedder.batch_size), desc="Embedding"):
            embeddings.extend(embedder.embed_documents(new_texts[i : i + embedder.batch_size]))

        store.upsert(ids=new_ids, texts=new_texts, metadatas=new_metas, embeddings=embeddings)
        total += len(chunks)

        print(f"Upserted {len(new_ids)} new chunks. DB total: {store.count()}")

    print(f"\nDone. Total chunks indexed this run: {total}")


if __name__ == "__main__":
    main()
