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

from build_vectorstore import get_vectorstore
import json

load_dotenv()

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
EMBEDDING_URL = "https://api.siliconflow.cn/v1"
EMBEDDING_MODEL = "BAAI/bge-m3"

MODEL="deepseek-flash"
MODEL_URL=os.getenv("MODEL_URL")
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")


def format_docs(docs):

    docs="\n".join(
        f"[{d.metadata.get('document_title', '未知法规')} {d.metadata.get('chapter', '')} {d.metadata.get('article_number', '')}]"
        for d in docs
    )
    print(f"{docs}")
    return docs

def get_questions(path:str):
    data=[]
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if not line:
                continue
            data.append(json.loads(line))

    questions=[q["测试问题"] for q in data] 
    return questions
    

def build_rag_chain():

    vector_store=get_vectorstore("M15_collection")

    # question = "公司与员工签订两年固定期限劳动合同，可以约定多长试用期？哪些合同不能约定试用期？"
    # print(vector_store._embedding_function.embed_query(question))

    # 3.进行检索，返回检索到的chunks
    retriever=vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 15},
    )

    questions=get_questions("data/企业用工合规rag系统评测问题集.jsonl")
    print(f"共有{len(questions)}条问题")

    call_chunks=retriever.batch(
        questions
)
    print(f"检索{len(call_chunks)}条问题的召回")

    for i,chunks in enumerate(call_chunks):
        print(f"问题{i}")
        format_docs(chunks)
        print("\n")

    return call_chunks



if __name__=="__main__":
    rag_chain=build_rag_chain()


    




