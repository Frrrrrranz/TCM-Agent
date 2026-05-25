"""
配伍禁忌检查 MCP 工具。

使用规则引擎确定性检查十八反、十九畏及毒性药物警告。
"""

from __future__ import annotations

from ..rag.pipeline import RAGPipeline


class DrugInteractionTool:
    """配伍禁忌检查工具。"""

    name = "tcm_drug_interaction_check"
    description = "检查药物配伍禁忌（十八反、十九畏、毒性药物警告）"
    parameters = {
        "type": "object",
        "properties": {
            "herbs": {
                "type": "array",
                "items": {"type": "string"},
                "description": "需要检查的药物列表（如：半夏、乌头）",
            },
        },
        "required": ["herbs"],
    }

    def __init__(self, pipeline: RAGPipeline) -> None:
        self.pipeline = pipeline

    async def execute(self, herbs: list[str]) -> str:
        """执行配伍禁忌检查。"""
        return await self.pipeline.check_drug_interaction(herbs)
