#!/usr/bin/env python3
"""最小感知工具 MCP 服务器：只注册 web_search 一个工具。"""

import logging

from pydantic import Field
from mcp.server import MCPServer

from tools import search_web          # 原项目的搜索实现

logging.basicConfig(level=logging.INFO)

mcp = MCPServer(
    "perception-tools",
    instructions="Minimal perception MCP server exposing only web_search.",
)


@mcp.tool(description="Search the web using DuckDuckGo (free, no API key required)")
async def web_search(
    query: str = Field(description="Search query string"),
    num_results: int = Field(default=5, description="Number of results (1-10)"),
    region: str = Field(default="wt-wt", description="Region code (e.g., 'us-en', 'wt-wt')"),
):
    """Search the web and return results."""
    return await search_web(query, num_results, region)


if __name__ == "__main__":
    logging.info("Starting minimal perception MCP server...")
    mcp.run(transport="stdio")