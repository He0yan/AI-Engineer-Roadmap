# src/vector_store.py
from pathlib import Path
import json
import chromadb
from embeddings import embed_texts


CHROMA_DIR = Path("data/chroma_db")
COLLECTION_NAME = "employment_law"
CHUNKS_PATH = Path("data/processed/all_chunks.json")


def get_client():
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def get_collection(client):
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def load_chunks():
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(f"未找到 {CHUNKS_PATH}，请先运行 D3 的 chunk_documents.py")
    return json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))


def build_index(rebuild: bool = False):
    
    client = get_client()

    if rebuild:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"[INFO] 已删除旧 collection: {COLLECTION_NAME}")
        except Exception:
            pass

    collection = get_collection(client)
    chunks = load_chunks()

    existing = collection.count()
    if existing > 0 and not rebuild:
        print(f"[SKIP] collection 中已有 {existing} 条记录，如需重建请传 rebuild=True")
        return

    ids = [c["chunk_id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [
        {
            "document_title": c["document_title"],
            "chapter": c.get("chapter", ""),
            "article_number": c["article_number"],
            "article_index": c.get("article_index", 0),
            "source_url": c.get("source_url", ""),
            "version": c.get("version", ""),
            "verification_date": c.get("verification_date", ""),
            "source_file": c.get("source_file", ""),
            "source_type": c.get("source_type", ""),
        }
        for c in chunks
    ]

    print(f"[INFO] 正在编码 {len(texts)} 个 Chunk ...")
    vectors = embed_texts(texts)

    # 分批写入，避免单次 add 过大
    batch_size = 64
    for i in range(0, len(ids), batch_size):
        collection.add(
            ids=ids[i:i + batch_size],
            embeddings=vectors[i:i + batch_size],
            documents=texts[i:i + batch_size],
            metadatas=metadatas[i:i + batch_size],
        )
        print(f"[OK] 已写入 {min(i + batch_size, len(ids))}/{len(ids)}")

    print(f"[OK] 入库完成，collection 总数: {collection.count()}")


def query(question: str, top_k: int = 5):
    client = get_client()
    collection = get_collection(client)
    q_vector = embed_texts([question])[0]
    #print(f"M14中q_vector长度为:{len(q_vector)}\n{q_vector[0:10]}")

    results = collection.query(
        query_embeddings=[q_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    return results


if __name__ == "__main__":
    import sys
    if "--rebuild" in sys.argv:
        build_index(rebuild=True)
    else:
        build_index()