"""
中药查询 MCP 工具。

支持按名称精确查询、按性味归经筛选、关键词模糊搜索。
"""

from __future__ import annotations

from typing import Optional
from ..rag.pipeline import RAGPipeline


class SearchHerbTool:
    """中药查询工具。"""

    name = "tcm_search_herb"
    description = "查询中药信息，支持按名称、四气、五味、归经、关键词搜索"
    parameters = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "中药名（精确匹配，如：桂枝、麻黄）",
            },
            "nature": {
                "type": "string",
                "description": "四气筛选（寒、热、温、凉、平）",
            },
            "taste": {
                "type": "string",
                "description": "五味筛选（酸、苦、甘、辛、咸）",
            },
            "meridian": {
                "type": "string",
                "description": "归经筛选（如：心、肺、膀胱经）",
            },
            "keywords": {
                "type": "string",
                "description": "关键词模糊搜索（在名称、功效、主治中搜索）",
            },
        },
    }

    def __init__(self, pipeline: RAGPipeline) -> None:
        self.pipeline = pipeline

    async def execute(
        self,
        name: Optional[str] = None,
        nature: Optional[str] = None,
        taste: Optional[str] = None,
        meridian: Optional[str] = None,
        keywords: Optional[str] = None,
    ) -> str:
        """执行中药查询。"""
        return await self.pipeline.search_herb(
            name=name,
            nature=nature,
            taste=taste,
            meridian=meridian,
            keywords=keywords,
        )
