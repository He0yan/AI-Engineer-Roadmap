import os
import requests
import numpy as np
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("SILICONFLOW_API_KEY")
EMBEDDING_URL = "https://api.siliconflow.cn/v1/embeddings"
MODEL_NAME = "BAAI/bge-m3"


def embed_texts(texts: list, batch_size: int = 32) -> list:
    """把一批文本编码成归一化向量，返回 list[list[float]]。"""
    if not API_KEY:
        raise RuntimeError("环境变量 SILICONFLOW_API_KEY 未设置")
    if not texts:
        return []

    all_vectors = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]

        response = requests.post(
            EMBEDDING_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "input": batch,
                "model": MODEL_NAME,
            },
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()

        # 按 index 排序，确保与输入顺序一致
        items = sorted(result["data"], key=lambda x: x["index"])
        vectors = [item["embedding"] for item in items]

        all_vectors.extend(vectors)

    return all_vectors