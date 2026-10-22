# check_retrieval.py
from vector_store import query

question = "用人单位与劳动者订立劳动合同，应该遵循哪些原则？"
results = query(question, top_k=5)

for i, (doc_id, doc, meta, dist) in enumerate(zip(
    results["ids"][0],
    results["documents"][0],
    results["metadatas"][0],
    results["distances"][0],
), start=1):
    print(f"\n--- Top {i} ---")
    print(f"chunk_id: {doc_id}")
    print(f"document_title: {meta.get('document_title')}")
    print(f"article_number: {meta.get('article_number')}")
    print(f"distance: {dist:.4f}")
    print(f"text: {doc[:200]}...")

