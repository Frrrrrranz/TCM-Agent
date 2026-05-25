"""Shared source traceability fields for structured TCM records."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TraceabilityFields(BaseModel):
    """Fields used to link structured records back to source material."""

    source_file: str = Field(default="", description="原始 Markdown 或种子文件路径")
    source_heading: str = Field(default="", description="原文标题或条目标题")
    source_text: str = Field(default="", description="对应原文片段")
    source_hash: str = Field(default="", description="原文片段哈希")
    parser_version: str = Field(default="seed-v1", description="解析脚本版本")
    review_status: str = Field(default="approved", description="复核状态")
    review_note: str = Field(default="", description="复核备注")
