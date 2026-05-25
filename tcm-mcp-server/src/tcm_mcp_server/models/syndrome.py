"""证型数据模型。"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field
from .traceability import TraceabilityFields


class Syndrome(TraceabilityFields):
    """证型完整数据模型。"""
    id: int = Field(description="唯一标识")
    name: str = Field(description="证型名")
    category: str = Field(description="辨证分类（八纲/脏腑/六经/卫气营血/气血津液）")
    key_symptoms: str = Field(description="关键症状")
    tongue: str = Field(default="", description="舌象")
    pulse: str = Field(default="", description="脉象")
    mechanism: str = Field(default="", description="病机")
    treatment_principle: str = Field(default="", description="治法")
    source: str = Field(default="", description="数据来源")


class SyndromeCreate(TraceabilityFields):
    """证型创建参数。"""
    name: str = Field(description="证型名")
    category: str = Field(description="辨证分类")
    key_symptoms: str = Field(default="", description="关键症状")
    tongue: str = Field(default="", description="舌象")
    pulse: str = Field(default="", description="脉象")
    mechanism: str = Field(default="", description="病机")
    treatment_principle: str = Field(default="", description="治法")
    source: str = Field(default="", description="数据来源")


class SyndromeSearchParams(BaseModel):
    """证型查询参数。"""
    name: Optional[str] = Field(default=None, description="证型名（精确匹配）")
    category: Optional[str] = Field(default=None, description="辨证分类筛选")
    symptoms: Optional[str] = Field(default=None, description="症状关键词语义搜索")
