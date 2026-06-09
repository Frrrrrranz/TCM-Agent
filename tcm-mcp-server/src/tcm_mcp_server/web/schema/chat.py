from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Any, List

class WebSocketMessage(BaseModel):
    """
    WebSocket 通信数据模型。
    用于在前端与 Python 后端网关之间传输聊天文本、工具调用状态和错误信息。
    """
    type: str = Field(
        ..., 
        description="消息类型，如 user_message, progress_message, assistant_message, tool_start, tool_result, turn_complete, error"
    )
    content: Optional[str] = Field(None, description="流式产生的文本内容或报错详情")
    toolName: Optional[str] = Field(None, description="调用的工具名")
    input: Optional[Any] = Field(None, description="工具输入参数")
    output: Optional[str] = Field(None, description="工具返回的结果")
    is_error: Optional[bool] = Field(None, alias="isError", description="工具执行或大模型请求是否失败")
    messages: Optional[List[dict[str, Any]]] = Field(None, description="Turn 结束后的完整消息历史")
    modelName: Optional[str] = Field(None, description="init 帧携带的模型名称，用于前端动态展示")
    session_id: Optional[str] = Field(None, alias="sessionId", description="当前会话的 UUID")
    request_id: Optional[str] = Field(None, alias="requestId", description="当前对话轮次的 UUID")

    class Config:
        populate_by_name = True
