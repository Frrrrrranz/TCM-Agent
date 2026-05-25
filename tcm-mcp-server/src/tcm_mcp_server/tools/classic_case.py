"""
医案检索 MCP 工具。

通过关键词和证型检索相关经典医案。
"""

from __future__ import annotations

from typing import Optional
from ..rag.pipeline import RAGPipeline


class ClassicCaseTool:
    """医案检索工具。"""

    name = "tcm_classic_case_search"
    description = "检索经典医案，支持按关键词和证型搜索"
    parameters = {
        "type": "object",
        "properties": {
            "keywords": {
                "type": "string",
                "description": "搜索关键词（如：桂枝汤、头痛发热）",
            },
            "syndrome": {
                "type": "string",
                "description": "证型筛选（如：太阳中风证）",
            },
        },
        "required": ["keywords"],
    }

    def __init__(self, pipeline: RAGPipeline) -> None:
        self.pipeline = pipeline

    async def execute(
        self,
        keywords: str,
        syndrome: Optional[str] = None,
    ) -> str:
        """执行医案检索。"""
        return await self.pipeline.search_classic_case(
            keywords=keywords,
            syndrome=syndrome,
        )
