
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import requests
from dotenv import load_dotenv


# 复用 D4 的余弦相似度实现
from similarity import cosine_similarity_numpy


# 项目路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]

VECTOR_PATH = (
    PROJECT_ROOT / "experiments" / "fault_embeddings.npz"
)
INFO_PATH = (
    PROJECT_ROOT / "experiments" / "embedding_metadata.json"
)
RESULT_PATH = PROJECT_ROOT / "experiments" / "results.csv"

# 查询必须使用与知识库相同的 Embedding 模型
MODEL_NAME = "BAAI/bge-m3"
API_URL = "https://api.siliconflow.cn/v1/embeddings"

TOP_K = 3


load_dotenv()

def load_knowledge_base():
    """加载已经生成并保存的文本向量。"""

    if not VECTOR_PATH.exists():
        raise FileNotFoundError(
            f"没有找到向量文件：{VECTOR_PATH}\n"
            "请先完成 D3 的向量生成步骤。"
        )

    if not INFO_PATH.exists():
        raise FileNotFoundError(
            f"没有找到模型元数据：{INFO_PATH}"
        )

    with INFO_PATH.open("r", encoding="utf-8") as f:
        metadata = json.load(f)

    stored_model = metadata.get("model_name")

    if stored_model != MODEL_NAME:
        raise ValueError(
            f"向量文件记录的模型是 {stored_model!r}，"
            f"当前查询模型是 {MODEL_NAME!r}。"
            "请确认两边使用同一个模型。"
        )

    with np.load(VECTOR_PATH, allow_pickle=False) as data:
        ids = data["ids"].tolist()
        texts = data["texts"].tolist()
        categories = data["categories"].tolist()
        embeddings = data["embeddings"]

    if embeddings.ndim != 2:
        raise ValueError("知识库向量必须是二维矩阵。")

    if len(ids) != embeddings.shape[0]:
        raise ValueError("ID 数量与向量数量不一致。")

    if len(texts) != len(ids) or len(categories) != len(ids):
        raise ValueError("文本、类别与 ID 数量不一致。")

    if not np.isfinite(embeddings).all():
        raise ValueError("知识库向量中存在 NaN 或无穷大。")

    return ids, texts, categories, embeddings


def embed_query(query, api_key):
    """调用 SiliconFlow API，将单条查询转换为向量。"""

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL_NAME,
            "input": query,
            "encoding_format": "float",
        },
        timeout=60,
    )

    if not response.ok:
        raise RuntimeError(
            f"Embedding API 请求失败：HTTP {response.status_code}\n"
            f"{response.text[:1000]}"
        )

    result = response.json()
    data = result.get("data", [])

    if len(data) != 1:
        raise RuntimeError(
            f"查询应返回 1 个向量，实际返回 {len(data)} 个。"
        )

    query_vector = np.asarray(
        data[0]["embedding"],
        dtype=np.float32,
    )

    if query_vector.ndim != 1:
        raise ValueError("查询向量不是一维数组。")

    if not np.isfinite(query_vector).all():
        raise ValueError("查询向量中存在 NaN 或无穷大。")

    if np.linalg.norm(query_vector) == 0:
        raise ValueError("查询得到零向量，无法进行有效比较。")

    return query_vector


def semantic_search(
    query,
    ids,
    texts,
    categories,
    embeddings,
    api_key,
    top_k=TOP_K,
):
    """计算查询与所有记录的余弦相似度，返回 Top-K。"""

    if not query.strip():
        raise ValueError("查询内容不能为空。")

    if not 1 <= top_k <= len(texts):
        raise ValueError("top_k 必须在 1 到记录总数之间。")

    # 第一步：生成查询向量
    query_vector = embed_query(query, api_key)

    # 第二步：检查查询与知识库向量维度是否一致
    if query_vector.shape[0] != embeddings.shape[1]:
        raise ValueError(
            f"查询向量维度为 {query_vector.shape[0]}，"
            f"知识库向量维度为 {embeddings.shape[1]}。"
            "请检查模型是否一致。"
        )

    # 第三步：计算查询与每条记录的余弦相似度
    scores = np.asarray(
        [
            cosine_similarity_numpy(query_vector, vector)
            for vector in embeddings
        ],
        dtype=np.float64,
    )

    # 第四步：按相似度从高到低排序
    ranked_indices = np.argsort(scores)[::-1][:top_k]

    hits = []

    for rank, index in enumerate(ranked_indices, start=1):
        hits.append({
            "rank": rank,
            "id": ids[index],
            "text": texts[index],
            "category": categories[index],
            "score": float(scores[index]),
        })

    return hits


def save_results(query, hits):
    """将查询结果追加到 CSV，供后续实验分析使用。"""

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)

    write_header = (
        not RESULT_PATH.exists()
        or RESULT_PATH.stat().st_size == 0
    )

    fieldnames = [
        "timestamp_utc",
        "model",
        "query",
        "rank",
        "id",
        "category",
        "score",
        "text",
    ]

    with RESULT_PATH.open(
        "a",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        if write_header:
            writer.writeheader()

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        for hit in hits:
            writer.writerow({
                "timestamp_utc": timestamp,
                "model": MODEL_NAME,
                "query": query,
                "rank": hit["rank"],
                "id": hit["id"],
                "category": hit["category"],
                "score": f'{hit["score"]:.8f}',
                "text": hit["text"],
            })


def main():
    # 1. 获取 API Key
    api_key = os.getenv("SILICONFLOW_API_KEY")

    if not api_key:
        raise RuntimeError(
            "未设置 SILICONFLOW_API_KEY 环境变量。"
        )

    # 2. 加载知识库，只需加载一次
    ids, texts, categories, embeddings = load_knowledge_base()

    print("=" * 60)
    print("工业设备故障语义搜索")
    print(f"模型：{MODEL_NAME}")
    print(f"知识库记录数：{len(texts)}")
    print(f"向量矩阵形状：{embeddings.shape}")
    print(f"返回数量：Top-{TOP_K}")
    print("输入 q 退出程序")
    print("=" * 60)

    # 3. 持续接收用户查询
    while True:
        try:
            query = input("\n请输入故障描述：").strip()

            if query.lower() == "q":
                print("搜索结束。")
                break

            if not query:
                print("查询不能为空，请重新输入。")
                continue

            # 4. 执行语义搜索
            hits = semantic_search(
                query=query,
                ids=ids,
                texts=texts,
                categories=categories,
                embeddings=embeddings,
                api_key=api_key,
                top_k=TOP_K,
            )

            # 5. 输出排序结果
            print("\n===== Top-3 搜索结果 =====")

            for hit in hits:
                print(
                    f'\n排名：{hit["rank"]}'
                    f' | ID：{hit["id"]}'
                    f' | 类别：{hit["category"]}'
                )
                print(f'相似度：{hit["score"]:.6f}')
                print(f'文本：{hit["text"]}')

            # 6. 保存实际实验结果
            save_results(query, hits)
            print(f"\n结果已追加至：{RESULT_PATH}")

        except (requests.RequestException, RuntimeError, ValueError) as exc:
            print(f"\n本次搜索未完成：{exc}")
            print("请检查网络、API 配额、模型配置及向量文件。")


if __name__ == "__main__":
    main()
