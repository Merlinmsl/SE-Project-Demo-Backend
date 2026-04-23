"""
Inspect what subject values are stored in the ChromaDB collection.
"""
from app.rag.vectorstore import ChromaVectorStore

store = ChromaVectorStore()
print("Total chunks:", store.count())

# Peek at metadata of first 5 results
result = store.collection.get(limit=5, include=["metadatas"])
metadatas = result.get("metadatas", [])
print("\nSample metadata (first 5 chunks):")
for i, m in enumerate(metadatas):
    print(f"  [{i}]", m)

# Get distinct subject values
all_meta = store.collection.get(include=["metadatas"])["metadatas"]
subjects = set(m.get("subject", "MISSING") for m in all_meta)
print("\nDistinct 'subject' values in ChromaDB:", subjects)
