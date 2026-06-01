from __future__ import annotations

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..service.agent_service import AgentService
from ..schema.chat import WebSocketMessage

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket 聊天服务路由端点。
    接收前端连接，启动 Node.js Agent 长驻子进程，
    按行监听用户输入消息，调度 AgentService 驱动核心 Agent，
    并将运行状态、工具调用进程、模型响应文本实时推回前端。
    """
    agent_service = AgentService()
    await websocket.accept()
    logger.info("Web 客户端已成功建立 WebSocket 链接 (/ws/chat)")

    # NOTE: WebSocket 连接建立后立即启动 Agent 子进程，
    # 将 init 帧（含真实模型名称）推送给前端，替代前端的硬编码默认值
    init_result = await agent_service.start()
    if init_result:
        await websocket.send_json(
            init_result.model_dump(by_alias=True, exclude_none=True)
        )
        if init_result.type == "error":
            logger.error("Agent 引擎启动失败，将在用户发送消息时重试")

    try:
        while True:
            # 1. 监听并解析前端发送的 JSON 数据
            data = await websocket.receive_json()
            user_content = data.get("content", "").strip()
            history = data.get("history")

            if not user_content:
                await websocket.send_json(
                    WebSocketMessage(
                        type="error",
                        content="诊断输入不能为空"
                    ).model_dump(by_alias=True, exclude_none=True)
                )
                continue

            history_len = len(history) if history else 0
            logger.info("收到前端提问: '%s', 历史上下文消息数: %d", user_content, history_len)

            # 2. 调度业务层服务，异步获取流式通信帧并推往前端
            async for response_frame in agent_service.run_agent_turn(user_content, history):
                await websocket.send_json(
                    response_frame.model_dump(by_alias=True, exclude_none=True)
                )

    except WebSocketDisconnect:
        logger.info("客户端已断开 WebSocket 链接")
    except Exception as exc:
        logger.exception("WebSocket 传输层捕获到未处理的运行时异常")
        try:
            await websocket.send_json(
                WebSocketMessage(
                    type="error",
                    content=f"服务器发生致命错误: {str(exc)}"
                ).model_dump(by_alias=True, exclude_none=True)
            )
        except Exception:
            pass
    finally:
        # WebSocket 断开时清理 Agent 子进程资源
        await agent_service.stop()
        logger.info("Agent 子进程资源已清理")
