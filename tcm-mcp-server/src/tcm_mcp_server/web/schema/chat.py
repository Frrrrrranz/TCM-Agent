from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

PROTOCOL_VERSION = 1
MessageType = Literal["user_message", "cancel_turn", "heartbeat"]
OutputType = Literal[
    "init",
    "heartbeat_ack",
    "tool_start",
    "tool_result",
    "assistant_message",
    "progress_message",
    "turn_complete",
    "turn_cancelled",
    "error",
]


class ClientMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    protocol_version: Literal[PROTOCOL_VERSION] = Field(
        PROTOCOL_VERSION, alias="protocolVersion"
    )
    type: MessageType
    session_id: str = Field(..., min_length=1, max_length=128, alias="sessionId")
    request_id: str | None = Field(None, min_length=1, max_length=128, alias="requestId")
    sequence: int = Field(..., ge=0)
    content: str | None = Field(None, min_length=1, max_length=12000)
    cursor: int | None = Field(None, ge=0)


class WebSocketMessage(BaseModel):
    """Validated v1 frame exchanged between the web gateway and Node Agent."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    protocol_version: Literal[PROTOCOL_VERSION] = Field(
        PROTOCOL_VERSION, alias="protocolVersion"
    )
    type: OutputType
    session_id: str | None = Field(None, max_length=128, alias="sessionId")
    request_id: str | None = Field(None, max_length=128, alias="requestId")
    sequence: int = Field(0, ge=0)
    tool_use_id: str | None = Field(None, max_length=128, alias="toolUseId")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content: str | None = Field(None, max_length=12000)
    tool_name: str | None = Field(None, max_length=256, alias="toolName")
    input: Any | None = None
    output: str | None = Field(None, max_length=20000)
    is_error: bool | None = Field(None, alias="isError")
    messages: list[dict[str, Any]] | None = None
    model_name: str | None = Field(None, max_length=256, alias="modelName")
    streaming: bool | None = None
