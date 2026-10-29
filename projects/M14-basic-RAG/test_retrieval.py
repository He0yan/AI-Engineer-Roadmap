# test_retrieval.py
from vector_store import query

question = "公司与员工签订两年固定期限劳动合同,可以约定多长试用期,哪些合同不能约定试用期"
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

