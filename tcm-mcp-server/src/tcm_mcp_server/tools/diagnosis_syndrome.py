"""
辨证分析 MCP 工具。

根据症状、舌象、脉象进行辨证分析，返回可能的证型及置信度。
"""

from __future__ import annotations

from typing import Optional
from ..rag.pipeline import RAGPipeline


class DiagnosisSyndromeTool:
    """辨证分析工具。"""

    name = "tcm_diagnosis_syndrome"
    description = "根据症状、舌象、脉象进行辨证分析，返回可能的证型及置信度"
    parameters = {
        "type": "object",
        "properties": {
            "symptoms": {
                "type": "array",
                "items": {"type": "string"},
                "description": "症状列表（如：头痛、发热、恶风）",
            },
            "tongue": {
                "type": "string",
                "description": "舌象描述（如：舌淡红、苔薄白）",
            },
            "pulse": {
                "type": "string",
                "description": "脉象描述（如：脉浮缓、脉浮紧）",
            },
        },
        "required": ["symptoms"],
    }

    def __init__(self, pipeline: RAGPipeline) -> None:
        self.pipeline = pipeline

    async def execute(
        self,
        symptoms: list[str],
        tongue: Optional[str] = None,
        pulse: Optional[str] = None,
    ) -> str:
        """执行辨证分析。"""
        return await self.pipeline.diagnose_syndrome(
            symptoms=symptoms,
            tongue=tongue,
            pulse=pulse,
        )
