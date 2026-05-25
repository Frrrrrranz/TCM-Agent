"""
穴位查询 MCP 工具。

支持按名称、归经、关键词搜索穴位信息。
"""

from __future__ import annotations

from typing import Optional
from ..rag.pipeline import RAGPipeline


class AcupointSearchTool:
    """穴位查询工具。"""

    name = "tcm_acupoint_search"
    description = "查询穴位信息，支持按名称、归经、关键词搜索"
    parameters = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "穴位名（精确匹配，如：足三里、合谷）",
            },
            "meridian": {
                "type": "string",
                "description": "归经筛选（如：足阳明胃经、手太阴肺经）",
            },
            "keywords": {
                "type": "string",
                "description": "关键词搜索（在名称、定位、主治中搜索）",
            },
        },
    }

    def __init__(self, pipeline: RAGPipeline) -> None:
        self.pipeline = pipeline

    async def execute(
        self,
        name: Optional[str] = None,
        meridian: Optional[str] = None,
        keywords: Optional[str] = None,
    ) -> str:
        """执行穴位查询。"""
        return await self.pipeline.search_acupoint(
            name=name,
            meridian=meridian,
            keywords=keywords,
        )
