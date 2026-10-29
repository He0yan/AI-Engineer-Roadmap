import os
import requests
from dotenv import load_dotenv


load_dotenv()

docs= ["apple", "banana", "fruit", "vegetable"]

url = "https://api.siliconflow.cn/v1/rerank"
headers = {
    "Authorization": f"Bearer {os.environ.get('SILICONFLOW_API_KEY')}",
    "Content-Type": "application/json"
}
payload = {
    "model": "BAAI/bge-reranker-v2-m3",
    "query": "apple",
    "documents": docs,
    "top_n": 4
}

response = requests.post(url, json=payload, headers=headers)

response=response.json()

reranked = response["results"]
top_docs = [
    docs[r["index"]]
    for r in reranked
]

print(top_docs)