import json
import os
from pathlib import Path
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from dotenv import load_dotenv

from build_vectorstore import get_vectorstore
import requests


load_dotenv()

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
EMBEDDING_URL = "https://api.siliconflow.cn/v1"
EMBEDDING_MODEL = "BAAI/bge-m3"

MODEL="deepseek-flash"
MODEL_URL=os.getenv("MODEL_URL")
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")


def format_docs(docs):

    docs="\n\n".join(
        f"[{d.metadata.get('document_title', '未知法规')} {d.metadata.get('chapter', '')} {d.metadata.get('article_number', '')}]\n{d.page_content}"
        for d in docs
    )
    print(f"重排序后的法条：{docs}")
    return docs

def rerank_documents(query: str, docs: list[Document],
                     top_n: int = 5, threshold: float = 0.1) -> list[Document]:
    """调用 SiliconFlow rerank API 对候选文档精排。失败时回退原始顺序。"""
    if not docs:
        return []

    payload = {
        "model": "BAAI/bge-reranker-v2-m3",
        "query": query,
        "documents": [d.page_content for d in docs],
        "top_n": top_n,
        "return_documents": False,
    }
    try:
        resp = requests.post(
            "https://api.siliconflow.cn/v1/rerank",
            headers={
                "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json()["results"]          # ← 关键：先 .json() 再取 results
    except Exception as e:
        print(f"[warn] rerank 失败，回退原始召回：{e}")
        return docs[:top_n]

    # 用 index 映射回原始 docs；results 已按分数降序
    reranked = [
        docs[r["index"]]
        for r in results
        if r["relevance_score"] >= threshold
    ]
    if not reranked:
        print(f"[warn] rerank 后无文档超过阈值 {threshold}，回退 Top-{top_n}")
        return docs[:top_n]
    return reranked
    

def build_rag_chain():

    vector_store=get_vectorstore("M15_collection")

    # question = "公司与员工签订两年固定期限劳动合同，可以约定多长试用期？哪些合同不能约定试用期？"
    # print(vector_store._embedding_function.embed_query(question))

    # 3.进行检索，返回检索到的chunks
    retriever=vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 10},
    )

    def retrieve_and_rerank(question: str) -> list[Document]:
        candidates = retriever.invoke(question)
        print(f"召回 {len(candidates)} 条 → rerank")
        #print(f"召回的法条{[doc[:20] for doc in format_docs(candidates)]}")
        reranked = rerank_documents(question, candidates, top_n=5, threshold=0.3)
        print(f"rerank 后保留 {len(reranked)} 条")
        return reranked

    llm = ChatOpenAI(
        model="deepseek-flash",
        base_url=MODEL_URL,
        api_key=OPENAI_API_KEY
    )

    prompt = ChatPromptTemplate.from_template(
        """你是一个企业用工合规助手。请严格依据以下检索到的法规片段回答问题。
    如果片段不足以支持结论，请明确说明“检索到的依据不足”，不要猜测法条。


    检索到的法规：
    {context}

    用户问题：{question}
    """
    )

    rag_chain = (
    {"context": RunnableLambda(retrieve_and_rerank)| format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)
    return rag_chain





if __name__=="__main__":
    rag_chain=build_rag_chain()

    question = "公司没有法定理由直接解除员工合同。员工可以主张哪些主要救济？经济补偿和违法解除赔偿金有什么区别？"
    
    print(f"模型回答：\n{rag_chain.invoke(question)}")
    




