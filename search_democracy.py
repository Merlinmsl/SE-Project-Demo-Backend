from app.rag.vectorstore import ChromaVectorStore

store = ChromaVectorStore()
res = store.collection.get(
    where_document={"$contains": "democracy"},
    include=["metadatas", "documents"]
)

print(f"Found {len(res['documents'])} chunks containing 'democracy'")
for i in range(min(5, len(res['documents']))):
    print(f"\n--- Chunk {i} ---")
    print(f"Metadata: {res['metadatas'][i]}")
    print(f"Text: {res['documents'][i][:500]}...")
