
import os
import requests

api_key = os.getenv("SILICONFLOW_API_KEY")

response = requests.post(
    "https://api.siliconflow.cn/v1/embeddings",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    },
    json={
        "input": ["电机运行温度超过正常范围"],
        "model": "BAAI/bge-m3",
    },
    timeout=60,
)

response.raise_for_status()
result = response.json()

embedding = result["data"][0]["embedding"]

print("模型名称：", result["model"])
print("向量维度：", len(embedding))
print("前 8 个数值：", embedding[:8])

print(len(result["data"]))
