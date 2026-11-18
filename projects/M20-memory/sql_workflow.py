"""SQL Agent 模板：MCP 工具 + LangGraph workflow + 多轮记忆。

分层：
    config  →  纯配置
    helpers →  纯函数（无状态）
    prompts →  提示词常量
    SQLAgent →  工具持有者 + 节点 + 图构建（消除全局状态）
    chat_loop →  IO 主循环（只负责输入输出）
"""

import asyncio
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langchain.mcp import MCPAdapter
from langchain.messages import AIMessage, ToolMessage
from langchain_core.messages import trim_messages
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from langchain_core.messages.utils import count_tokens_approximately


load_dotenv()

# ==================== 1. 配置 ====================
MODEL = "gpt-6-luna"
MODEL_URL = os.getenv("MODEL_URL")
API_KEY = os.getenv("API_KEY")
MCP_SERVER_PATH = Path(__file__).resolve().parent / "mcp_server.py"
MAX_HISTORY_TOKENS = 4000

model = ChatOpenAI(model=MODEL, base_url=MODEL_URL, api_key=API_KEY)


# ==================== 2. 无状态辅助函数 ====================
def content_to_text(content) -> str:
    """MCP 工具返回的 content 可能是 str，也可能是内容块 list，统一转纯文本。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    return str(content)


async def load_mcp_tools():
    """连接 MCP 服务器，返回 LangChain Tool 列表。"""
    async with MCPAdapter(target=MCP_SERVER_PATH) as adapter:
        return await adapter.list_tools()


# ==================== 3. 提示词 ====================
GENERATE_QUERY_PROMPT = """
You are an agent designed to interact with a SQL database. Please answer in Chinese.
Given an input question, create a syntactically correct sql query to run,
then look at the results of the query and return the answer. Unless the user
specifies a specific number of examples they wish to obtain, always limit your
query to at most 5 results.

You can order the results by a relevant column to return the most interesting
examples in the database. Never query for all the columns from a specific table,
only ask for the relevant columns given the question.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.
""".strip()

CHECK_QUERY_PROMPT = """
You are a SQL expert with a strong attention to detail.
Double check the sql query for common mistakes, including:
- Using NOT IN with NULL values
- Using UNION when UNION ALL should have been used
- Using BETWEEN for exclusive ranges
- Data type mismatch in predicates
- Properly quoting identifiers
- Using the correct number of arguments for functions
- Casting to the correct data type
- Using the proper columns for joins

If there are any of the above mistakes, rewrite the query. If there are no mistakes,
just reproduce the original query.

You will call the appropriate tool to execute the query after running this check.
""".strip()


# ==================== 4. Agent 类 ====================
class SQLAgent:
    """持有工具、定义节点、构建图。所有节点统一 async，无全局状态。"""

    def __init__(self, tools):
        # 工具作为实例属性，替代原来的 global 变量
        self.list_tables_tool = next(t for t in tools if t.name == "sql_db_list_tables")
        self.get_schema_tool = next(t for t in tools if t.name == "sql_db_schema")
        self.run_query_tool = next(t for t in tools if t.name == "sql_db_query")

    # ---------- 节点 ----------
    async def list_tables(self, state: MessagesState):
        tool_call = {
            "name": "sql_db_list_tables",
            "args": {},
            "id": "list_tables_call",
            "type": "tool_call",
        }
        tool_call_message = AIMessage(content="", tool_calls=[tool_call])
        tool_message = await self.list_tables_tool.ainvoke(tool_call)
        response = AIMessage(f"Available tables: {content_to_text(tool_message.content)}")
        return {"messages": [tool_call_message, tool_message, response]}

    async def call_get_schema(self, state: MessagesState):
        llm = model.bind_tools([self.get_schema_tool], tool_choice="any")
        response = await llm.ainvoke(state["messages"])
        return {"messages": [response]}

    async def generate_query(self, state: MessagesState):
        llm = model.bind_tools([self.run_query_tool])
        # 历史裁剪：保留最近 MAX_HISTORY_TOKENS 的内容，system prompt 单独加回
        history = trim_messages(
            state["messages"],
            max_tokens=MAX_HISTORY_TOKENS,
            strategy="last",
            token_counter=count_tokens_approximately,  # 近似计数器,
            include_system=False,
            allow_partial=False,
        )
        messages = [{"role": "system", "content": GENERATE_QUERY_PROMPT}, *history]
        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    async def check_query(self, state: MessagesState):
        # 取 generate_query 刚产出的那条带 tool_call 的 AI 消息
        last_ai = state["messages"][-1]
        tool_call = last_ai.tool_calls[0]
        user_message = {"role": "user", "content": tool_call["args"]["query"]}
        llm = model.bind_tools([self.run_query_tool], tool_choice="any")
        response = await llm.ainvoke(
            [{"role": "system", "content": CHECK_QUERY_PROMPT}, user_message]
        )
        # 让 check_query 的响应"接管"原 AI 消息的 id，
        # 避免历史里出现两条指向同一次查询的 tool_calls
        response.id = last_ai.id
        return {"messages": [response]}

    # ---------- 路由 ----------
    @staticmethod
    def route_start(state: MessagesState) -> Literal["list_tables", "generate_query"]:
        """已有 schema 就直接进入生成，避免每轮重复初始化。"""
        for msg in state["messages"]:
            if isinstance(msg, ToolMessage) and msg.name == "sql_db_schema":
                return "generate_query"
        return "list_tables"

    @staticmethod
    def should_continue(state: MessagesState) -> Literal[END, "check_query"]:
        if not state["messages"][-1].tool_calls:
            return END
        return "check_query"

    # ---------- 构图 ----------
    def build(self, checkpointer=None):
        get_schema_node = ToolNode([self.get_schema_tool], name="get_schema")
        run_query_node = ToolNode([self.run_query_tool], name="run_query")

        builder = StateGraph(MessagesState)
        builder.add_node("list_tables", self.list_tables)
        builder.add_node("call_get_schema", self.call_get_schema)
        builder.add_node("get_schema", get_schema_node)
        builder.add_node("generate_query", self.generate_query)
        builder.add_node("check_query", self.check_query)
        builder.add_node("run_query", run_query_node)

        builder.add_conditional_edges(
            START,
            self.route_start,
            {"list_tables": "list_tables", "generate_query": "generate_query"},
        )
        builder.add_edge("list_tables", "call_get_schema")
        builder.add_edge("call_get_schema", "get_schema")
        builder.add_edge("get_schema", "generate_query")
        builder.add_conditional_edges("generate_query", self.should_continue)
        builder.add_edge("check_query", "run_query")
        builder.add_edge("run_query", "generate_query")

        return builder.compile(checkpointer=checkpointer or InMemorySaver())


# ==================== 5. 主循环（只做 IO） ====================
async def chat_loop(agent, thread_id: str = "thread-001"):
    config = {"configurable": {"thread_id": thread_id}}
    while True:
        try:
            question = input("\n用户:").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if question.lower() in ("exit", "quit", "q"):
            break
        if not question:
            continue

        try:
            stream = await agent.astream_events(
                {"messages": [{"role": "user", "content": question}]},
                config,
                version="v3",
            )
            async for message in stream.messages:
                printed = False 
                async for token in message.text:
                    print(token, end="", flush=True)
                    printed = True
                if printed:
                    print()   # ← 每条 message 结束后换行
        except Exception as e:
            # 单轮失败不退出进程，便于长会话调试
            print(f"\n[错误] {type(e).__name__}: {e}")


# ==================== 6. 入口 ====================
async def main():
    tools = await load_mcp_tools()
    agent = SQLAgent(tools).build()
    await chat_loop(agent)


if __name__ == "__main__":
    asyncio.run(main())