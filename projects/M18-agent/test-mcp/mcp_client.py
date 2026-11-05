#!/usr/bin/env python3
"""最小 MCP 客户端示例：只调用 web_search 一个工具。

原实验脚本的 fixture、receipt、哈希、验收、安全探针全部去掉，
只保留学习 MCP 必须的四步。
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client


import os

SERVER = Path(__file__).resolve().parent /  "mcp_server.py"


async def demo() -> None:
    # 1. 告诉 SDK 怎么启动服务器子进程
    params = StdioServerParameters(
        command=sys.executable,      # 用当前 Python，避免环境不一致
        args=[str(SERVER)],          # 服务器入口 src/main.py
    )

    # 2. stdio_client 启动子进程并建立 stdin/stdout 管道
    #    Client 进入时完成 MCP 初始化握手（协议版本协商、能力交换）
    async with Client(stdio_client(params)) as client:

        # 3. 对应 MCP 的 tools/list
        listed = await client.list_tools()
        print(f"服务器提供了 {len(listed.tools)} 个工具")
        print("前 5 个:", [t.name for t in listed.tools[:5]])

        # 4. 对应 MCP 的 tools/call
        result = await client.call_tool(
            "web_search",
            arguments={"query": "Dzongsar Khyentse Rinpoche", "num_results": 3},
        )

        # 结果优先看 structuredContent，没有就取 content 里的文本
        payload = (
            getattr(result, "structuredContent", None)
            or getattr(result, "structured_content", None)
            or [getattr(item, "text", item) for item in result.content]
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    asyncio.run(demo())

