"""中药数据模型。"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field
from .traceability import TraceabilityFields


class Herb(TraceabilityFields):
    """中药完整数据模型。"""
    id: int = Field(description="唯一标识")
    name: str = Field(description="中药名")
    pinyin: str = Field(description="拼音")
    category: str = Field(description="分类（如：解表药、清热药）")
    nature: str = Field(description="四气（寒、热、温、凉、平）")
    taste: str = Field(description="五味（酸、苦、甘、辛、咸）")
    meridian: str = Field(description="归经（如：心、肺、膀胱经）")
    toxicity: str = Field(default="无毒", description="毒性说明")
    effect: str = Field(description="功效")
    indication: str = Field(description="主治")
    usage: str = Field(default="", description="用法用量")
    caution: str = Field(default="", description="使用注意/禁忌")
    source: str = Field(default="", description="数据来源")


class HerbCreate(TraceabilityFields):
    """中药创建参数。"""
    name: str = Field(description="中药名")
    pinyin: str = Field(default="", description="拼音")
    category: str = Field(default="", description="分类")
    nature: str = Field(default="平", description="四气")
    taste: str = Field(default="甘", description="五味")
    meridian: str = Field(default="", description="归经")
    toxicity: str = Field(default="无毒", description="毒性")
    effect: str = Field(default="", description="功效")
    indication: str = Field(default="", description="主治")
    usage: str = Field(default="", description="用法用量")
    caution: str = Field(default="", description="使用注意")
    source: str = Field(default="", description="数据来源")


class HerbSearchParams(BaseModel):
    """中药查询参数。"""
    name: Optional[str] = Field(default=None, description="中药名（精确匹配）")
    nature: Optional[str] = Field(default=None, description="四气筛选")
    taste: Optional[str] = Field(default=None, description="五味筛选")
    meridian: Optional[str] = Field(default=None, description="归经筛选")
    keywords: Optional[str] = Field(default=None, description="关键词语义搜索")
