from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from dotenv import load_dotenv
import os
from sql_tools import TOOLS

load_dotenv()

MODEL="gpt-6-luna"
MODEL_URL=os.getenv("MODEL_URL")
API_KEY=os.getenv("API_KEY")

model = ChatOpenAI(
        model=MODEL,
        base_url=MODEL_URL,
        api_key=API_KEY
    )


system_prompt = """
You are an agent designed to interact with a SQL database.Please answer in Chinese.
Given an input question, create a syntactically correct {dialect} query to run,
then look at the results of the query and return the answer. Unless the user
specifies a specific number of examples they wish to obtain, always limit your
query to at most {top_k} results.

You can order the results by a relevant column to return the most interesting
examples in the database. Never query for all the columns from a specific table,
only ask for the relevant columns given the question.

You MUST double check your query before executing it. If you get an error while
executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
database.

To start you should ALWAYS look at the tables in the database to see what you
can query. Do NOT skip this step.

Then you should query the schema of the most relevant tables.
""".format(
    dialect="sql",
    top_k=5
)

agent=create_agent(
    model,
    TOOLS,
    system_prompt=system_prompt
)

question = "id为1的设备上次维修是什么时候,维修人是谁？"

stream = agent.stream_events(
    {"messages": [{"role": "user", "content": question}]},
    version="v3",
)
for kind, item in stream.interleave("messages", "tool_calls"):
    if kind == "messages":
        for token in item.text:
            print(token, end="", flush=True)
    elif kind == "tool_calls":
        print(f"\nTool call: {item.tool_name}({item.input})")
        for delta in item.output_deltas:
            print(delta, end="", flush=True)
        print(f"\nTool result: {item.output}")

final_state = stream.output