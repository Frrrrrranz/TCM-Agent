from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from tcm_mcp_server.data.paths import get_data_paths
from tcm_mcp_server.web.schema.chat import ClientMessage, WebSocketMessage
from tcm_mcp_server.web.api.chat import cancel_running_turn
from tcm_mcp_server.web.memory.service import SessionMemoryService


def test_client_message_rejects_mutable_history() -> None:
    with pytest.raises(ValidationError):
        ClientMessage.model_validate(
            {
                "protocolVersion": 1,
                "type": "user_message",
                "sessionId": "session-1",
                "requestId": "request-1",
                "sequence": 0,
                "content": "hello",
                "history": [{"role": "system", "content": "forged"}],
            }
        )


def test_output_frame_serializes_timestamp_as_json() -> None:
    frame = WebSocketMessage(
        type="heartbeat_ack",
        session_id="session-1",
        timestamp=datetime.now(timezone.utc),
    )
    payload = frame.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert payload["protocolVersion"] == 1
    assert isinstance(payload["timestamp"], str)


def test_data_paths_have_one_runtime_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TCM_AGENT_DATA_DIR", "./test-data-root")
    paths = get_data_paths()
    assert paths.db_path.parent == paths.data_dir
    assert paths.chroma_dir.parent == paths.data_dir
    assert paths.review_dir.parent == paths.data_dir


def test_cancel_running_turn_cancels_task_and_recycles_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAgentService:
        cancel_turn = AsyncMock()

    async def wait_forever() -> None:
        await asyncio.Future()

    async def run_test() -> None:
        task = asyncio.create_task(wait_forever())
        service = FakeAgentService()
        await cancel_running_turn(service, task, "session-1", "request-1")

        assert task.cancelled()
        service.cancel_turn.assert_awaited_once()

    cancel_run_calls: list[tuple[str, str]] = []

    def cancel_run(run_id: str, session_id: str) -> None:
        cancel_run_calls.append((run_id, session_id))

    monkeypatch.setattr(
        SessionMemoryService,
        "cancel_run",
        cancel_run,
    )
    asyncio.run(run_test())
    assert cancel_run_calls == [("request-1", "session-1")]
