

# src/retriever.py
from embeddings import embed_texts
from vector_store import get_client, get_collection

DEFAULT_TOP_K = 5


def retrieve(question: str, top_k: int = DEFAULT_TOP_K) -> list:
    """对问题做向量检索，返回结构化的候选条文列表。

    返回结构：
    [
        {
            "rank": 1,
            "chunk_id": "...",
            "document_title": "...",
            "chapter": "...",
            "article_number": "...",
            "text": "...",
            "source_url": "...",
            "distance": 0.2228,
        },
        ...
    ]
    """
    if not question or not question.strip():
        return []

    client = get_client()
    collection = get_collection(client)

    q_vector = embed_texts([question])[0]

    results = collection.query(
        query_embeddings=[q_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for rank, (chunk_id, doc, meta, dist) in enumerate(zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ), start=1):
        hits.append({
            "rank": rank,
            "chunk_id": chunk_id,
            "document_title": meta.get("document_title", ""),
            "chapter": meta.get("chapter", ""),
            "article_number": meta.get("article_number", ""),
            "text": doc,
            "source_url": meta.get("source_url", ""),
            "distance": dist,
        })

    return hits


def format_hits(hits: list) -> str:
    """把检索结果格式化成可读文本，便于调试和日志。"""
    lines = []
    for h in hits:
        lines.append(
            f"[{h['rank']}] {h['document_title']} {h['article_number']} "
            f"(distance={h['distance']:.4f})\n"
            f"    chunk_id: {h['chunk_id']}\n"
            f"    text: {h['text'][:160]}{'...' if len(h['text']) > 160 else ''}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    q = "用人单位与劳动者订立劳动合同，应该遵循哪些原则？"
    hits = retrieve(q, top_k=5)
    print(format_hits(hits))