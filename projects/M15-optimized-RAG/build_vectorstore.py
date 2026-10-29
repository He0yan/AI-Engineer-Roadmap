import json
import os
from pathlib import Path
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from dotenv import load_dotenv

load_dotenv()

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
EMBEDDING_URL = "https://api.siliconflow.cn/v1"
EMBEDDING_MODEL = "BAAI/bge-m3"

MODEL="deepseek-flash"
MODEL_URL=os.getenv("MODEL_URL")
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")

def chunks_to_documents(chunks: list[dict]) -> list[Document]:
    """把 chunk_documents.py 产出的 dict 列表转成 LangChain Document 列表。"""
    docs = []
    for c in chunks:
        # text 提到 page_content，其余字段全部进 metadata
        metadata = {k: v for k, v in c.items() if k != "text"}
        docs.append(
            Document(
                page_content=c["text"],
                metadata=metadata,
                id=c.get("chunk_id"),   # 用确定性 chunk_id 作为向量库 id
            )
        )
    return docs

def get_vectorstore(collection_name:str):
    embeddings = OpenAIEmbeddings(
    model=EMBEDDING_MODEL,
    base_url=EMBEDDING_URL,
    api_key=SILICONFLOW_API_KEY,
    check_embedding_ctx_length=False
    )

    
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory="./data/chroma_langchain_db"
    )
    return vector_store


def embedding(collection_name:str,batch_size=64):
    # 1.将切分好的chunks转为langchain Document格式
    chunks = json.loads(
        Path("data/all_chunks.json").read_text(encoding="utf-8")
    )
    docs = chunks_to_documents(chunks)
    print(f"转换后 Document 数量: {len(docs)}")

    vector_store=get_vectorstore(collection_name)

    all_ids=[]
    for i in range(0,len(docs),batch_size):
        batch=docs[i:i+batch_size]
        ids = vector_store.add_documents(documents=batch) #相同id的chunks重复入库会覆盖原来的chunks
        all_ids.extend(ids)
    print(f"已入库{len(all_ids)}条chunks")

    return vector_store


   



if __name__=="__main__":
    collection_name="M15_collection"
    embedding(collection_name)


