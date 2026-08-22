from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict, deque

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from ..memory.service import SessionMemoryService
from ..schema.chat import ClientMessage, WebSocketMessage
from ..service.agent_service import AgentService

logger = logging.getLogger(__name__)
router = APIRouter()

MESSAGE_WINDOW_SECONDS = 60.0
MAX_MESSAGES_PER_WINDOW = 30
message_timestamps: dict[str, deque[float]] = defaultdict(deque)


def is_allowed_origin(origin: str | None) -> bool:
    if not origin:
        return True
    configured = os.getenv("TCM_AGENT_ALLOWED_ORIGINS", "").strip()
    allowed = (
        {value.strip() for value in configured.split(",") if value.strip()}
        if configured
        else {"http://localhost:5173", "http://127.0.0.1:5173"}
    )
    return origin in allowed


def is_rate_limited(client_key: str) -> bool:
    now = time.monotonic()
    timestamps = message_timestamps[client_key]
    while timestamps and now - timestamps[0] > MESSAGE_WINDOW_SECONDS:
        timestamps.popleft()
    if len(timestamps) >= MAX_MESSAGES_PER_WINDOW:
        return True
    timestamps.append(now)
    return False


async def send_frame(websocket: WebSocket, frame: WebSocketMessage) -> None:
    await websocket.send_json(
        frame.model_dump(mode="json", by_alias=True, exclude_none=True)
    )


async def send_error(
    websocket: WebSocket,
    session_id: str,
    content: str,
    request_id: str | None = None,
) -> None:
    await send_frame(
        websocket,
        WebSocketMessage(
            type="error",
            session_id=session_id,
            request_id=request_id,
            content=content,
        ),
    )


async def receive_client_message(
    websocket: WebSocket,
    session_id: str,
) -> ClientMessage | None:
    raw_payload = await websocket.receive_text()
    if len(raw_payload.encode("utf-8")) > 64 * 1024:
        await send_error(websocket, session_id, "request_too_large")
        return None

    try:
        message = ClientMessage.model_validate_json(raw_payload)
    except ValidationError:
        await send_error(websocket, session_id, "invalid_protocol_message")
        return None

    if message.session_id != session_id:
        await send_error(
            websocket,
            session_id,
            "session_id_mismatch",
            message.request_id,
        )
        return None
    return message


async def stream_turn(
    agent_service: AgentService,
    output_queue: asyncio.Queue[WebSocketMessage | None],
    content: str,
    session_id: str,
    request_id: str,
) -> None:
    try:
        async for frame in agent_service.run_agent_turn(
            content,
            session_id=session_id,
            request_id=request_id,
        ):
            await output_queue.put(frame)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Agent turn task failed")
        await output_queue.put(
            WebSocketMessage(
                type="error",
                session_id=session_id,
                request_id=request_id,
                content="agent_turn_failed",
            )
        )
    finally:
        await output_queue.put(None)


async def cancel_running_turn(
    agent_service: AgentService,
    turn_task: asyncio.Task[None],
    session_id: str,
    request_id: str,
) -> None:
    turn_task.cancel()
    try:
        await turn_task
    except asyncio.CancelledError:
        pass
    await agent_service.cancel_turn()
    await asyncio.to_thread(SessionMemoryService.cancel_run, request_id, session_id)


async def wait_for_turn_or_control(
    websocket: WebSocket,
    agent_service: AgentService,
    output_queue: asyncio.Queue[WebSocketMessage | None],
    turn_task: asyncio.Task[None],
    session_id: str,
    request_id: str,
    expected_sequence: int,
    seen_request_ids: set[str],
    client_key: str,
) -> int:
    while True:
        receive_task: asyncio.Task[str] = asyncio.create_task(
            websocket.receive_text()
        )
        output_task: asyncio.Task[WebSocketMessage | None] = asyncio.create_task(
            output_queue.get()
        )
        done, pending = await asyncio.wait(
            {receive_task, output_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()

        if output_task in done:
            frame = output_task.result()
            if frame is None:
                await turn_task
                return expected_sequence
            await send_frame(websocket, frame)
            continue

        message = await receive_task
        if is_rate_limited(client_key):
            await send_error(websocket, session_id, "rate_limit_exceeded")
            continue
        if len(message.encode("utf-8")) > 64 * 1024:
            await send_error(websocket, session_id, "request_too_large")
            continue
        try:
            control = ClientMessage.model_validate_json(message)
        except ValidationError:
            await send_error(websocket, session_id, "invalid_protocol_message")
            continue
        if control.session_id != session_id:
            await send_error(websocket, session_id, "session_id_mismatch")
            continue
        if control.sequence != expected_sequence:
            await send_error(websocket, session_id, "sequence_mismatch")
            continue
        expected_sequence += 1

        if control.type == "heartbeat":
            await send_frame(
                websocket,
                WebSocketMessage(
                    type="heartbeat_ack",
                    session_id=session_id,
                    request_id=control.request_id,
                    sequence=control.sequence,
                ),
            )
            continue

        if control.type == "cancel_turn":
            if control.request_id != request_id:
                await send_error(
                    websocket,
                    session_id,
                    "request_id_mismatch",
                    control.request_id,
                )
                continue
            await cancel_running_turn(
                agent_service,
                turn_task,
                session_id,
                request_id,
            )
            await send_frame(
                websocket,
                WebSocketMessage(
                    type="turn_cancelled",
                    session_id=session_id,
                    request_id=request_id,
                ),
            )
            return expected_sequence

        if control.request_id and control.request_id not in seen_request_ids:
            seen_request_ids.add(control.request_id)
        await send_error(websocket, session_id, "turn_in_progress", control.request_id)


@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket) -> None:
    agent_service = AgentService()
    if not is_allowed_origin(websocket.headers.get("origin")):
        await websocket.close(code=1008, reason="origin_not_allowed")
        return
    await websocket.accept()

    raw_session_id = websocket.query_params.get("session_id") or websocket.query_params.get(
        "sessionId"
    )
    session_id = SessionMemoryService.get_or_create_session(raw_session_id)
    expected_sequence = 0
    seen_request_ids: set[str] = set()
    client_key = websocket.client.host if websocket.client else "unknown"

    init_result = await agent_service.start()
    if init_result:
        init_result.session_id = session_id
        await send_frame(websocket, init_result)

    try:
        while True:
            message = await receive_client_message(websocket, session_id)
            if message is None:
                continue
            if is_rate_limited(client_key):
                await send_error(websocket, session_id, "rate_limit_exceeded")
                continue
            if message.sequence != expected_sequence:
                await send_error(websocket, session_id, "sequence_mismatch")
                continue
            expected_sequence += 1

            if message.type == "heartbeat":
                await send_frame(
                    websocket,
                    WebSocketMessage(
                        type="heartbeat_ack",
                        session_id=session_id,
                        request_id=message.request_id,
                        sequence=message.sequence,
                    ),
                )
                continue

            if not message.request_id:
                await send_error(websocket, session_id, "request_id_required")
                continue
            if message.request_id in seen_request_ids:
                await send_error(
                    websocket,
                    session_id,
                    "request_id_already_seen",
                    message.request_id,
                )
                continue
            seen_request_ids.add(message.request_id)

            if message.type == "cancel_turn":
                await send_frame(
                    websocket,
                    WebSocketMessage(
                        type="turn_cancelled",
                        session_id=session_id,
                        request_id=message.request_id,
                    ),
                )
                continue
            if not message.content:
                await send_error(
                    websocket,
                    session_id,
                    "content_required",
                    message.request_id,
                )
                continue

            request_id = await asyncio.to_thread(
                SessionMemoryService.start_run,
                session_id,
                message.content,
                message.request_id,
            )
            output_queue: asyncio.Queue[WebSocketMessage | None] = asyncio.Queue()
            turn_task = asyncio.create_task(
                stream_turn(
                    agent_service,
                    output_queue,
                    message.content,
                    session_id,
                    request_id,
                )
            )
            expected_sequence = await wait_for_turn_or_control(
                websocket,
                agent_service,
                output_queue,
                turn_task,
                session_id,
                request_id,
                expected_sequence,
                seen_request_ids,
                client_key,
            )
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception:
        logger.exception("Unhandled WebSocket transport error")
        try:
            await send_error(websocket, session_id, "websocket_transport_error")
        except Exception:
            pass
    finally:
        await agent_service.stop()
