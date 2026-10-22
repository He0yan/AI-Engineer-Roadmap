
import numpy as np
from pathlib import Path


def cosine_similarity_numpy(a, b):
    """
    使用 NumPy 计算两个向量的余弦相似度。

    本实验约定：
    - 两个向量必须是一维数组，且长度相同。
    - 输入不能包含 NaN 或无穷大。
    - 如果任何一个向量是零向量，返回 0.0。
      这是工程约定，不是数学公式对零向量的定义。
    """
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)

    if a.ndim != 1 or b.ndim != 1:
        raise ValueError("输入必须是一维向量。")

    if a.shape != b.shape:
        raise ValueError("两个向量的维度必须相同。")

    if a.size == 0:
        raise ValueError("向量不能为空。")

    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("向量不能包含 NaN 或无穷大。")

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    # 零向量单独处理，避免除以零
    if norm_a == 0 or norm_b == 0:
        return 0.0

    # 计算点积
    dot_product = np.dot(a, b)

    # 计算余弦相似度
    score = dot_product / (norm_a * norm_b)

    # 避免浮点数误差造成极小的越界
    return float(np.clip(score, -1.0, 1.0))


def main():
    # 使用 D3 已保存的数据，检查真实文本向量
    root = Path(__file__).resolve().parents[1]
    vector_path = (
        root / "experiments" / "fault_embeddings.npz"
    )

    if not vector_path.exists():
        print(f"没有找到向量文件：{vector_path}")
        print("请先完成 D3 的 Embedding 数据生成。")
        return

    with np.load(vector_path, allow_pickle=False) as data:
        ids = data["ids"].tolist()
        texts = data["texts"].tolist()
        categories = data["categories"].tolist()
        embeddings = data["embeddings"]

    if embeddings.shape[0] != len(ids):
        raise ValueError("向量数量与记录数量不一致。")

    index_by_id = {
        record_id: i for i, record_id in enumerate(ids)
    }

    # 选择几个实际文本对进行比较
    pairs = [
        ("F001", "F002"),
        ("F001", "F003"),
        ("F001", "F006"),
        ("F001", "F011"),
        ("F001", "F017"),
    ]

    print("实际向量矩阵形状：", embeddings.shape)
    print("\n===== 真实文本向量相似度 =====")

    for id_a, id_b in pairs:
        if id_a not in index_by_id or id_b not in index_by_id:
            print(f"找不到记录：{id_a} 或 {id_b}")
            continue

        i = index_by_id[id_a]
        j = index_by_id[id_b]

        score = cosine_similarity_numpy(
            embeddings[i],
            embeddings[j],
        )

        print(f"\n{id_a} [{categories[i]}]")
        print(f"  {texts[i]}")
        print(f"{id_b} [{categories[j]}]")
        print(f"  {texts[j]}")
        print(f"Cosine Similarity: {score:.6f}")


if __name__ == "__main__":
    main()
