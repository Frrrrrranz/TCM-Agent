"""
TCM MCP Server 入口。

注册所有中医药 MCP 工具，通过 stdio 协议与 mini-code 通信。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from .data.database import Database
from .rag.embeddings import EmbeddingManager
from .rag.vector_store import VectorStore
from .rag.retriever import HybridRetriever
from .rag.pipeline import RAGPipeline
from .tools import (
    SearchHerbTool,
    SearchPrescriptionTool,
    DiagnosisSyndromeTool,
    DrugInteractionTool,
    AcupointSearchTool,
    ClassicCaseTool,
)

logger = logging.getLogger(__name__)

# 数据目录配置
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DB_PATH = DATA_DIR / "tcm.db"
CHROMA_DIR = DATA_DIR / "chroma"


def create_server() -> object:
    """
    创建并配置 MCP Server，注册所有工具。

    使用 MCP Python SDK 创建 server，初始化数据库和 RAG 引擎，
    注册 6 个中医药工具。
    """
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import Tool, TextContent
    except ImportError:
        logger.error("mcp 包未安装，请执行: pip install mcp")
        sys.exit(1)

    # ── 初始化数据层 ──────────────────────────────────────────

    db = Database(DB_PATH)
    db.connect()

    # ── 初始化 RAG 引擎 ───────────────────────────────────────

    embedding_manager = EmbeddingManager()
    vector_store = VectorStore(CHROMA_DIR)
    retriever = HybridRetriever(db, vector_store)
    pipeline = RAGPipeline(retriever)

    # ── 初始化工具 ────────────────────────────────────────────

    tools = [
        SearchHerbTool(pipeline),
        SearchPrescriptionTool(pipeline),
        DiagnosisSyndromeTool(pipeline),
        DrugInteractionTool(pipeline),
        AcupointSearchTool(pipeline),
        ClassicCaseTool(pipeline),
    ]

    # ── 创建 MCP Server ───────────────────────────────────────

    server = Server("tcm-mcp-server")

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """返回所有注册的工具列表。"""
        return [
            Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.parameters,
            )
            for tool in tools
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str,
        arguments: dict | None,
    ) -> list[TextContent]:
        """执行工具调用。"""
        if arguments is None:
            arguments = {}

        # 查找匹配的工具
        for tool in tools:
            if tool.name == name:
                result = await tool.execute(**arguments)
                return [TextContent(type="text", text=result)]

        raise ValueError(f"未知工具: {name}")

    return server


def main() -> None:
    """主入口：启动 MCP Server。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("正在启动 TCM MCP Server...")
    logger.info("数据库路径: %s", DB_PATH)
    logger.info("向量库路径: %s", CHROMA_DIR)

    server = create_server()

    from mcp.server.stdio import stdio_server
    import anyio

    async def _run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    anyio.run(_run)


if __name__ == "__main__":
    main()
