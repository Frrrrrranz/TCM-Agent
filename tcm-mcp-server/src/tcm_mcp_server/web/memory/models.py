from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field


class ToolInvocationRecord(BaseModel):
    """单次工具调用的数据模型。"""
    id: Optional[int] = Field(None, description="自增主键")
    run_id: str = Field(..., description="所属对话轮次的 UUID")
    tool_name: str = Field(..., description="被调用的工具名称")
    input: Optional[str] = Field(None, description="工具输入的 JSON 字符串")
    output: Optional[str] = Field(None, description="工具输出的 JSON 字符串")
    is_error: bool = Field(False, description="工具执行是否报错")
    created_at: str = Field(..., description="创建时间 ISO 字符串")


class ConversationRun(BaseModel):
    """单次问诊（一轮对话）的数据模型。"""
    id: str = Field(..., description="当前轮次的 UUID")
    session_id: str = Field(..., description="所属会话的 UUID")
    user_content: str = Field(..., description="用户输入的提问文本")
    assistant_content: Optional[str] = Field(None, description="大模型助手的回复文本")
    tool_calls_json: Optional[str] = Field(None, description="工具调用列表序列化后的 JSON 字符串")
    created_at: str = Field(..., description="创建时间 ISO 字符串")
    status: str = Field("success", description="当前轮次执行状态 (success 或 failed)")


class ConversationSession(BaseModel):
    """问诊会话头信息数据模型。"""
    id: str = Field(..., description="会话的 UUID")
    title: Optional[str] = Field(None, description="会话标题，默认为用户首次提问")
    run_count: int = Field(0, description="对话轮次总数")
    created_at: str = Field(..., description="创建时间 ISO 字符串")
    updated_at: str = Field(..., description="更新时间 ISO 字符串")
