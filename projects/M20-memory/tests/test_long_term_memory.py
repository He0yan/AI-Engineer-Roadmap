from langgraph.graph import StateGraph,MessagesState,START
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.config import get_store


import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

MODEL="gpt-6-luna"
MODEL_URL=os.getenv("MODEL_URL")
API_KEY=os.getenv("API_KEY")

model = ChatOpenAI(
        model=MODEL,
        base_url=MODEL_URL,
        api_key=API_KEY
    )



store=InMemoryStore()
namespace=("1","user-1","preferences")
store.put(namespace,"风格",{"value": "基于佛教的理论回答问题"})

def call_model_node(state:MessagesState):
    store=get_store()
    style=store.get(namespace,"风格")
    style=style.value["value"]
    messages = state["messages"]
    if style:
        messages = [SystemMessage(content=f"回答风格要求：{style}")] + messages

    response=model.invoke(messages)
    return {"messages":response}

builder=StateGraph(MessagesState)
builder.add_node("call_model",call_model_node)
builder.add_edge(START,"call_model")

graph=builder.compile(checkpointer=InMemorySaver(),store=store)


config={"configurable":{"thread_id":"thread-1"}}


result=graph.invoke(
    {"messages":[HumanMessage(content=f"你好，我想找一个好看的女生谈恋爱而不得，很痛苦。")]},
    config=config
)

print(f"第1轮对话结果:\n{result}\n")

result=graph.invoke(
    {"messages":[HumanMessage(content="你能用佛教唯识学的理论来分析我的痛苦吗？")]},
    config=config
)

print(f"第2轮对话结果:\n{result}\n")


