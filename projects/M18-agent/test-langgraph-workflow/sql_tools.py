import sqlite3
from langchain.tools import tool
from sqlalchemy import text, create_engine
from sqlalchemy.exc import SQLAlchemyError
import re
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

# 连接字符串：postgresql+psycopg2://用户:密码@主机:端口/数据库名
DATABASE_URL = "postgresql+psycopg2://postgres:12345@localhost:5432/industrial_ai"

# 1. 创建引擎（管理连接池）
engine = create_engine(DATABASE_URL, echo=True)

MAX_ROWS = 50          # 最多返回多少行
MAX_CELL_LEN = 200     # 单个单元格最多显示多少字符

_WRITE_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY|CALL|DO|VACUUM|REINDEX)\b",
    re.IGNORECASE,
)


MODEL="gpt-6-luna"
MODEL_URL=os.getenv("MODEL_URL")
API_KEY=os.getenv("API_KEY")

model = ChatOpenAI(
        model=MODEL,
        base_url=MODEL_URL,
        api_key=API_KEY
    )

@tool
def sql_db_list_tables(_: str = "") -> str:
    """List all user tables in the current PostgreSQL database.

    Use this first when you need to know what data is available.
    Input: empty string.
    Output: comma-separated table names, or an error message.
    """
    sql = text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)

    try:
        with engine.connect() as conn:
            rows = conn.execute(sql).fetchall()
        tables = [row[0] for row in rows]
        return ", ".join(tables) if tables else "(数据库中没有用户表)"
    except SQLAlchemyError as e:
        return f"查询失败: {e}"

@tool
def sql_db_schema(table_names: str) -> str:
    """Input to this tool is a comma-separated list of tables, output is the schema and sample rows for those tables.
    Be sure that the tables actually exist by calling sql_db_list_tables first!
    Example Input: table1, table2, table3"""
    results = []
    with engine.connect() as conn:
        for table in table_names.split(","):
            table = table.strip()

            # 1) 取列定义；查不到 = 表不存在（省掉单独的 whitelist 查询）
            cols = conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :t
                ORDER BY ordinal_position;
            """), {"t": table}).fetchall()

            if not cols:
                results.append(f"Error: table_names {{{table!r}}} not found in database")
                continue

            # 2) 拼一个简化的 CREATE TABLE
            lines = [f'CREATE TABLE "{table}" (']
            for name, dtype, nullable, default in cols:
                line = f'\t"{name}" {dtype.upper()}'
                if nullable == "NO":
                    line += " NOT NULL"
                if default is not None:
                    line += f" DEFAULT {default}"
                lines.append(line)
            lines.append(")")
            results.append("\n".join(lines))

            # 3) 样本行
            quoted = '"' + table.replace('"', '""') + '"'
            try:
                res = conn.execute(text(f"SELECT * FROM {quoted} LIMIT 3;"))
                rows = res.fetchall()
                if rows:
                    header = "\t".join(res.keys())
                    body = "\n".join("\t".join(str(x) for x in r) for r in rows)
                    results.append(f"/*\n3 rows from {table} table:\n{header}\n{body}\n*/")
            except SQLAlchemyError as e:
                results.append(f"Error fetching sample rows: {e}")

    return "\n\n".join(results)

@tool
def sql_db_query(query: str) -> str:
    """Run a read-only SQL SELECT query on the PostgreSQL database.

    Use this after sql_db_list_tables and sql_db_schema, and only with
    tables/columns that actually exist.
    Input: exactly one SELECT (or WITH ... SELECT) statement.
    Output: a header line, a separator, then up to 50 data rows,
    or an error message.
    """
    q = query.strip().rstrip(";")

    # ---- 第一道：语法白名单 ----
    if not re.match(r"^\s*(SELECT|WITH)\b", q, re.IGNORECASE):
        return "只允许 SELECT / WITH ... SELECT 查询"

    if ";" in q:
        return "一次只允许执行一条 SQL 语句"

    if _WRITE_KEYWORDS.search(q):
        return "查询中不允许出现写操作关键字（INSERT/UPDATE/DELETE/DROP 等）"

    # ---- 第二道：数据库只读事务兜底 ----
    try:
        with engine.begin() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            result = conn.execute(text(q))
            columns = list(result.keys())
            rows = result.fetchmany(MAX_ROWS)
    except SQLAlchemyError as e:
        return f"查询失败: {e}"

    if not rows:
        return "查询结果为空（0 行）"

    # ---- 拼成对 LLM 友好的文本 ----
    def cell(v):
        if v is None:
            return "NULL"
        s = str(v)
        return s if len(s) <= MAX_CELL_LEN else s[:MAX_CELL_LEN] + "…"

    header = " | ".join(columns)
    body = "\n".join(
        " | ".join(cell(v) for v in row) for row in rows
    )
    out = f"{header}\n{'-' * len(header)}\n{body}"

    if len(rows) == MAX_ROWS:
        out += f"\n(仅显示前 {MAX_ROWS} 行，结果可能被截断)"
    return out

@tool
def sql_db_query_checker(query: str) -> str:
    """Use this tool to double check if your query is correct before executing it.
    Always use this tool before executing a query with sql_db_query!"""
    trigger_prompt = """{query}
Double check the sqlite query above for common mistakes, including:
- Using NOT IN with NULL values
- Using UNION when UNION ALL should have been used
- Using BETWEEN for exclusive ranges
- Data type mismatch in predicates
- Properly quoting identifiers
- Using the correct number of arguments for functions
- Casting to the correct data type
- Using the proper columns for joins

If there are any of the above mistakes, rewrite the query. If there are no mistakes, just reproduce the original query.

Output the final SQL query only.

SQL Query: """.format(query=query)

    response = model.invoke(trigger_prompt)
    return response.text.strip()

TOOLS = [sql_db_list_tables, sql_db_schema, sql_db_query, sql_db_query_checker]


if __name__ == "__main__":
    # Use a distinct loop variable so it does not shadow the `tool` decorator.
    for t in TOOLS:
        print(f"{t.name}: {t.description}\n")