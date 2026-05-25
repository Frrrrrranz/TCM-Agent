"""
方剂查询 MCP 工具。

支持按名称精确查询、按证型筛选、症状描述匹配、药物组成搜索。
"""

from __future__ import annotations

from typing import Optional
from ..rag.pipeline import RAGPipeline


class SearchPrescriptionTool:
    """方剂查询工具。"""

    name = "tcm_search_prescription"
    description = "查询方剂信息，支持按名称、证型、症状、药物组成搜索"
    parameters = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "方剂名（精确匹配，如：桂枝汤、麻黄汤）",
            },
            "syndrome": {
                "type": "string",
                "description": "证型筛选（如：太阳中风证、风寒束肺证）",
            },
            "symptoms": {
                "type": "string",
                "description": "症状描述（语义搜索，如：头痛发热恶风脉浮缓）",
            },
            "herbs": {
                "type": "string",
                "description": "包含的药物（逗号分隔，如：桂枝,白芍,甘草）",
            },
        },
    }

    def __init__(self, pipeline: RAGPipeline) -> None:
        self.pipeline = pipeline

    async def execute(
        self,
        name: Optional[str] = None,
        syndrome: Optional[str] = None,
        symptoms: Optional[str] = None,
        herbs: Optional[str] = None,
    ) -> str:
        """执行方剂查询。"""
        return await self.pipeline.search_prescription(
            name=name,
            syndrome=syndrome,
            symptoms=symptoms,
            herbs=herbs,
        )
