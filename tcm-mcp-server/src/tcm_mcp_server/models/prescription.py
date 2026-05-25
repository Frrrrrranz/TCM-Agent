"""方剂数据模型。"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field
from .traceability import TraceabilityFields


class Prescription(TraceabilityFields):
    """方剂完整数据模型。"""
    id: int = Field(description="唯一标识")
    name: str = Field(description="方剂名")
    source: str = Field(default="", description="出处")
    category: str = Field(default="", description="分类（如：解表剂、清热剂）")
    composition: str = Field(description="组成（药物及用量）")
    effect: str = Field(description="功用")
    indication: str = Field(description="主治")
    syndrome: str = Field(default="", description="证型")
    symptoms: str = Field(default="", description="典型症状")
    explanation: str = Field(default="", description="方解")
    addition: str = Field(default="", description="加减化裁")
    caution: str = Field(default="", description="使用注意")
    source_text: str = Field(default="", description="数据来源")


class PrescriptionCreate(TraceabilityFields):
    """方剂创建参数。"""
    name: str = Field(description="方剂名")
    source: str = Field(default="", description="出处")
    category: str = Field(default="", description="分类")
    composition: str = Field(default="", description="组成")
    effect: str = Field(default="", description="功用")
    indication: str = Field(default="", description="主治")
    syndrome: str = Field(default="", description="证型")
    symptoms: str = Field(default="", description="典型症状")
    explanation: str = Field(default="", description="方解")
    addition: str = Field(default="", description="加减化裁")
    caution: str = Field(default="", description="使用注意")
    source_text: str = Field(default="", description="数据来源")


class PrescriptionSearchParams(BaseModel):
    """方剂查询参数。"""
    name: Optional[str] = Field(default=None, description="方剂名（精确匹配）")
    syndrome: Optional[str] = Field(default=None, description="证型筛选")
    symptoms: Optional[str] = Field(default=None, description="症状关键词语义搜索")
    herbs: Optional[str] = Field(default=None, description="包含的药物（逗号分隔）")
