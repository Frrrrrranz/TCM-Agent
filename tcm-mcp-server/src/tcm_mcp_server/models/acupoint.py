"""穴位数据模型。"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field
from .traceability import TraceabilityFields


class Acupoint(TraceabilityFields):
    """穴位完整数据模型。"""
    id: int = Field(description="唯一标识")
    name: str = Field(description="穴位名")
    pinyin: str = Field(default="", description="拼音")
    meridian: str = Field(description="归经")
    location: str = Field(description="定位")
    indication: str = Field(description="主治")
    operation: str = Field(default="", description="操作手法")
    caution: str = Field(default="", description="注意事项")
    source: str = Field(default="", description="数据来源")


class AcupointCreate(TraceabilityFields):
    """穴位创建参数。"""
    name: str = Field(description="穴位名")
    pinyin: str = Field(default="", description="拼音")
    meridian: str = Field(default="", description="归经")
    location: str = Field(default="", description="定位")
    indication: str = Field(default="", description="主治")
    operation: str = Field(default="", description="操作手法")
    caution: str = Field(default="", description="注意事项")
    source: str = Field(default="", description="数据来源")


class AcupointSearchParams(BaseModel):
    """穴位查询参数。"""
    name: Optional[str] = Field(default=None, description="穴位名（精确匹配）")
    meridian: Optional[str] = Field(default=None, description="归经筛选")
    keywords: Optional[str] = Field(default=None, description="关键词搜索")
