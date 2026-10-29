import jieba
import json
from pathlib import Path
from langchain_community.retrievers import BM25Retriever
from build_vectorstore import chunks_to_documents

def chinese_tokenizer(text: str) -> list[str]:
    """使用 jieba 对中文文本进行分词。"""
    return list(jieba.cut(text))

chunks = json.loads(
    Path("data/all_chunks.json").read_text(encoding="utf-8")
)
docs = chunks_to_documents(chunks)
print(f"转换后 Document 数量: {len(docs)}")

bm25_retriever = BM25Retriever.from_documents(
    docs,
    k=10,  # 单路召回数量，Hybrid 融合时建议设大一些
    preprocess_func=chinese_tokenizer,
)

query = "固定期限合同到期时，员工处于医疗期或孕期/产期/哺乳期，公司是否都能按到期日终止？"
results = bm25_retriever.invoke(query)

for doc in results:
    print(f"条款: {doc.metadata.get('article_number')}, 内容: {doc.page_content[:100]}...")
