"""
Debug: inspect raw ChromaDB query results and distances.
"""
from app.rag.vectorstore import ChromaVectorStore
from app.rag.embedding import GeminiEmbedder
from app.rag.config import MAX_DISTANCE_FOR_MATCH

store = ChromaVectorStore()
embedder = GeminiEmbedder()

question = "What caused World War 1?"
print(f"Question: {question}")
print(f"MAX_DISTANCE_FOR_MATCH: {MAX_DISTANCE_FOR_MATCH}")
print()

q_vec = embedder.embed_query(question)
print(f"Query vector dim: {len(q_vec)}")

# First try WITHOUT subject filter
best, hits = store.query(query_embedding=q_vec, n_results=5, subject_filter=None)
print("--- Results WITHOUT subject filter ---")
for h in hits:
    print(f"  distance={h.distance:.4f}  subject={h.metadata.get('subject')}  file={h.metadata.get('source_file')}  pages={h.metadata.get('page_start')}-{h.metadata.get('page_end')}")
    print(f"  text[:100]: {h.text[:100]}")
    print()

# Now try WITH subject filter 'history'
print("--- Results WITH subject_filter='history' ---")
best2, hits2 = store.query(query_embedding=q_vec, n_results=5, subject_filter="history")
for h in hits2:
    print(f"  distance={h.distance:.4f}  subject={h.metadata.get('subject')}  pages={h.metadata.get('page_start')}-{h.metadata.get('page_end')}")

print()
if best:
    print(f"Best distance: {best.distance:.4f}")
    print(f"Is match (< {MAX_DISTANCE_FOR_MATCH}): {store.is_match(best)}")
