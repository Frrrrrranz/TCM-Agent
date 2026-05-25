from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


async def list_stdio_tools() -> set[str]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    env["PYTHONIOENCODING"] = "utf-8"

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "tcm_mcp_server.server"],
        cwd=str(PROJECT_ROOT),
        env=env,
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()
            return {tool.name for tool in result.tools}


def test_mcp_stdio_lists_tcm_tools() -> None:
    tool_names = asyncio.run(asyncio.wait_for(list_stdio_tools(), timeout=20))

    assert {
        "tcm_search_herb",
        "tcm_drug_interaction_check",
        "tcm_search_prescription",
    } <= tool_names
