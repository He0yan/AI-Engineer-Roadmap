
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

import numpy as np
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "fault_texts.json"
OUTPUT_DIR = PROJECT_ROOT / "experiments"
VECTOR_PATH = OUTPUT_DIR / "fault_embeddings.npz"
INFO_PATH = OUTPUT_DIR / "embedding_metadata.json"

API_URL = "https://api.siliconflow.cn/v1/embeddings"
MODEL_NAME = "BAAI/bge-m3"

load_dotenv()

def main():
    # 1. 从环境变量读取密钥
    
    api_key = os.getenv("SILICONFLOW_API_KEY")

    if not api_key:
        raise RuntimeError(
            "未设置 SILICONFLOW_API_KEY 环境变量。"
        )

    # 2. 读取工业故障数据
    with DATA_PATH.open("r", encoding="utf-8") as f:
        records = json.load(f)

    if not records:
        raise ValueError("数据文件中没有文本记录。")

    ids = [item["id"] for item in records]
    texts = [item["text"] for item in records]
    categories = [item["category"] for item in records]

    if not all(isinstance(t, str) and t.strip() for t in texts):
        raise ValueError("所有文本都必须是非空字符串。")

    # 3. 一次请求编码多条文本
    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL_NAME,
            "input": texts,
        },
        timeout=120,
    )

    # 如果 API 返回 HTTP 错误，显示原因
    if not response.ok:
        raise RuntimeError(
            f"Embedding API 请求失败："
            f"HTTP {response.status_code}\n"
            f"{response.text[:1000]}"
        )

    result = response.json()
    data = result.get("data", [])

    if len(data) != len(texts):
        raise RuntimeError(
            f"输入 {len(texts)} 条文本，"
            f"但 API 返回 {len(data)} 个向量。"
        )

    # 4. 根据 index 排序，保持向量与文本对应
    data = sorted(data, key=lambda item: item["index"])

    embeddings = np.asarray(
        [item["embedding"] for item in data],
        dtype=np.float32,
    )

    if embeddings.ndim != 2:
        raise RuntimeError("返回结果不是二维向量矩阵。")

    if not np.isfinite(embeddings).all():
        raise RuntimeError("向量中存在 NaN 或无穷大。")

    # 5. 查看实验结果
    print("模型：", result.get("model", MODEL_NAME))
    print("文本数量：", len(texts))
    print("向量矩阵形状：", embeddings.shape)
    print("向量维度：", embeddings.shape[1])
    print("NumPy 数据类型：", embeddings.dtype)
    print("第一条文本：", texts[0])
    print("第一条向量的前 8 个数值：", embeddings[0][:8])

    # 6. 保存向量、原始文本与记录信息
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        VECTOR_PATH,
        ids=np.asarray(ids),
        texts=np.asarray(texts),
        categories=np.asarray(categories),
        embeddings=embeddings,
    )

    metadata = {
        "model_name": MODEL_NAME,
        "record_count": len(texts),
        "embedding_dimension": int(embeddings.shape[1]),
        "embedding_dtype": str(embeddings.dtype),
        "client_normalization_applied": False,
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    with INFO_PATH.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # 7. 重新读取文件，检查保存结果
    with np.load(VECTOR_PATH, allow_pickle=False) as saved:
        loaded_vectors = saved["embeddings"]
        loaded_texts = saved["texts"]

        assert np.array_equal(loaded_texts, np.asarray(texts))
        assert np.allclose(loaded_vectors, embeddings)

    print("保存验证：通过")
    print("向量文件：", VECTOR_PATH)
    print("模型信息：", INFO_PATH)


if __name__ == "__main__":
    main()
