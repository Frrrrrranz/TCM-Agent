from __future__ import annotations

import os
import sys
import json
import logging
import time
import asyncio
import subprocess
import threading
from pathlib import Path
from typing import AsyncGenerator, Any, Optional
from queue import Queue, Empty

from ..schema.chat import WebSocketMessage

logger = logging.getLogger(__name__)


# 动态追溯定位 Node.js 项目根目录 (TCM-Agent/TCM-Agent)
def find_node_project_dir() -> Path:
    current = Path(__file__).resolve().parent
    for _ in range(10):
        pkg_json = current / "package.json"
        if pkg_json.exists():
            try:
                with open(pkg_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("name") == "mini-code":
                        return current
            except Exception:
                pass
        current = current.parent
    # 兜底退化方案
    return Path(__file__).resolve().parents[5]


NODE_PROJECT_DIR = find_node_project_dir()


class AgentService:
    """
    Agent 服务层。
    管理 Node.js Agent 核心进程的生命周期（长驻模式），
    通过 stdin/stdout 管道与其通信，并将输出流转换为统一的 Pydantic 模型。

    NOTE: 使用 subprocess.Popen 而非 asyncio.create_subprocess_shell，
    因为 Uvicorn 在 Windows reload 模式下使用 SelectorEventLoop，
    该循环不支持 asyncio 子进程创建。通过 Popen + 后台读取线程 + asyncio.Queue
    实现异步桥接，确保在任何事件循环策略下都能正常工作。
    """

    def __init__(self) -> None:
        self._process: Optional[subprocess.Popen[bytes]] = None
        self._model_name: str = "TCM-Agent"
        self._stdout_queue: Queue[Optional[str]] = Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def _stdout_reader(self) -> None:
        """
        后台线程：持续逐行读取子进程 stdout，将数据放入线程安全队列。
        当 stdout 关闭时放入 None 作为终止标记。
        """
        try:
            if self._process and self._process.stdout:
                for raw_line in self._process.stdout:
                    line = raw_line.decode("utf-8", errors="ignore").strip()
                    if line:
                        self._stdout_queue.put(line)
        except Exception as exc:
            logger.error("stdout 读取线程异常: %s", exc)
        finally:
            # None 信号表示 stdout 已关闭
            self._stdout_queue.put(None)

    async def start(self) -> Optional[WebSocketMessage]:
        """
        启动 Node.js 长驻子进程，读取 init 帧并返回。
        返回 init 帧 WebSocketMessage，若启动失败返回 error 帧。
        """
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                # 进程已在运行，直接返回 init 信息
                return WebSocketMessage(
                    type="init",
                    modelName=self._model_name
                )

            # 在 Windows 上 npm 是 .cmd 脚本，必须通过 shell 启动
            cmd = "npm run dev -- --json-mode"

            logger.info(
                "启动 Node.js Agent 长驻子进程。工作目录: %s, 运行命令: %s",
                NODE_PROJECT_DIR,
                cmd
            )

            # 复制当前进程的环境变量（包含 API Key）传递给子进程
            env = os.environ.copy()

            try:
                self._process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # 将 stderr 合并到 stdout，由读取线程流式处理，防止 Windows 阻塞并增强诊断
                    cwd=str(NODE_PROJECT_DIR),
                    env=env,
                    shell=True,
                )
            except Exception as exc:
                logger.exception("启动 Node.js 进程发生严重异常")
                return WebSocketMessage(
                    type="error",
                    content=f"启动 Node.js Agent 引擎失败: {str(exc)}"
                )

            # 启动后台 stdout 读取线程
            self._stdout_queue = Queue()
            self._reader_thread = threading.Thread(
                target=self._stdout_reader,
                daemon=True,
                name="agent-stdout-reader"
            )
            self._reader_thread.start()

        # 异步等待 init 帧，跳过 npm 启动时输出的非 JSON banner 行
        # NOTE: npm run dev 会先输出 "> mini-code@0.1.0 dev" 等信息，不是 JSON
        deadline = time.monotonic() + 15.0
        try:
            while time.monotonic() < deadline:
                remaining = max(0.1, deadline - time.monotonic())
                init_line = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._stdout_queue.get(timeout=remaining)
                )
                if init_line is None:
                    logger.error("Node.js Agent 子进程在发送 init 帧前就已退出")
                    self._kill_process_sync()
                    return WebSocketMessage(
                        type="error",
                        content="Node.js Agent 引擎启动后立即退出，请检查配置"
                    )

                # 尝试解析为 JSON，非 JSON 行跳过
                try:
                    init_data = json.loads(init_line)
                except json.JSONDecodeError:
                    logger.debug("跳过 npm 启动输出: %s", init_line)
                    continue

                if init_data.get("type") == "init":
                    self._model_name = init_data.get("modelName", "TCM-Agent")
                    logger.info("Node.js Agent 已就绪，模型: %s", self._model_name)
                    return WebSocketMessage(
                        type="init",
                        modelName=self._model_name
                    )

                # 如果是 JSON 但不是 init 帧，也跳过
                logger.debug("跳过非 init 类型帧: %s", init_line)

            # 超时未收到 init 帧
            logger.error("等待 Node.js Agent init 帧超时 (15s)")
            return WebSocketMessage(
                type="init",
                modelName=self._model_name
            )

        except Empty:
            logger.error("等待 Node.js Agent init 帧超时 (15s)")
            self._kill_process_sync()
            return WebSocketMessage(
                type="error",
                content="Node.js Agent 引擎启动超时，请检查 Node.js 环境和依赖"
            )
        except Exception as exc:
            logger.exception("解析 Node.js Agent init 帧时异常")
            self._kill_process_sync()
            return WebSocketMessage(
                type="error",
                content=f"解析 Agent 初始化信息失败: {str(exc)}"
            )

    async def run_agent_turn(
        self,
        user_content: str,
        history: list[dict[str, Any]] | None = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> AsyncGenerator[WebSocketMessage, None]:
        """
        向长驻 Node.js 子进程发送单轮交互请求，流式读取结果。
        """
        # 确保进程存活
        if self._process is None or self._process.poll() is not None:
            init_result = await self.start()
            if init_result and init_result.type == "error":
                yield init_result
                return

        if self._process is None or self._process.stdin is None:
            yield WebSocketMessage(
                type="error",
                content="Node.js Agent 引擎未就绪，请刷新页面重试"
            )
            return

        # 0. 载入 Session Memory 提取历史摘要
        from ..memory.service import SessionMemoryService
        history_context = ""
        if session_id:
            history_context = await asyncio.to_thread(
                SessionMemoryService.build_history_context, session_id
            )

        # 构建并发送交互负载到 stdin
        payload: dict[str, Any] = {
            "type": "user_message",
            "content": user_content
        }
        if history:
            payload["history"] = history
        if history_context:
            payload["history_context"] = history_context

        input_data = json.dumps(payload, ensure_ascii=False) + "\n"

        try:
            self._process.stdin.write(input_data.encode("utf-8"))
            self._process.stdin.flush()
        except Exception as exc:
            logger.exception("向子进程 stdin 写入交互负载时失败")
            yield WebSocketMessage(
                type="error",
                content=f"向 Agent 引擎发送输入失败: {str(exc)}"
            )
            self._kill_process_sync()
            return

        # 记录本轮数据以便落库
        tool_invocations: list[dict[str, Any]] = []
        assistant_content_accumulator: list[str] = []

        # 从 Queue 中流式读取输出行，通过线程池桥接到 asyncio
        loop = asyncio.get_event_loop()
        try:
            while True:
                line = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: self._stdout_queue.get(timeout=120.0)
                    ),
                    timeout=125.0  # 外层超时比内层大一点，作为安全兜底
                )

                if line is None:
                    # 子进程 stdout 关闭，说明进程已退出
                    logger.warning("Node.js Agent 子进程 stdout 已关闭")
                    self._kill_process_sync()
                    yield WebSocketMessage(
                        type="error",
                        content="Agent 引擎异常退出，请重新发送消息"
                    )
                    break

                try:
                    data = json.loads(line)
                    msg = WebSocketMessage(**data)
                    
                    # 动态灌入会话与请求标识，回传给前端
                    msg.session_id = session_id
                    msg.request_id = request_id
                    
                    yield msg

                    # 流式分析与记忆收集
                    if msg.type == "tool_start":
                        tool_invocations.append({
                            "tool_name": msg.toolName,
                            "input": msg.input,
                            "output": None,
                            "is_error": False
                        })
                    elif msg.type == "tool_result":
                        for tool in reversed(tool_invocations):
                            if tool["tool_name"] == msg.toolName and tool["output"] is None:
                                tool["output"] = msg.output
                                tool["is_error"] = msg.is_error or False
                                if request_id:
                                    await asyncio.to_thread(
                                        SessionMemoryService.record_tool_invocation,
                                        request_id,
                                        msg.toolName,
                                        tool["input"],
                                        msg.output,
                                        msg.is_error or False
                                    )
                                break
                    elif msg.type == "assistant_message" and msg.content:
                        assistant_content_accumulator.append(msg.content)

                    # turn_complete 标志着本轮对话结束，退出读取循环
                    if msg.type == "turn_complete":
                        if request_id and session_id:
                            assistant_content = "".join(assistant_content_accumulator)
                            await asyncio.to_thread(
                                SessionMemoryService.finish_run,
                                request_id,
                                session_id,
                                assistant_content,
                                tool_invocations
                            )
                        break
                except json.JSONDecodeError:
                    logger.warning("Node.js 打印了非 JSON 数据或错误日志: %s", line)
                except Exception as exc:
                    logger.warning("解析 Node.js 状态帧异常: %s, 原始内容: %s", exc, line)

        except (asyncio.TimeoutError, Empty):
            logger.error("读取 Node.js Agent 输出超时 (120s)")
            yield WebSocketMessage(
                type="error",
                content="Agent 推理超时（120 秒无响应），请缩短问题或重试"
            )
            self._kill_process_sync()
        except Exception as exc:
            logger.exception("读取子进程 stdout 管道时发生异常")
            yield WebSocketMessage(
                type="error",
                content=f"读取 Agent 输出流异常: {str(exc)}"
            )
            self._kill_process_sync()

    async def stop(self) -> None:
        """关闭 Node.js 长驻子进程，释放系统资源。"""
        self._kill_process_sync()

    def _kill_process_sync(self) -> None:
        """安全终止子进程并回收资源（同步方法）。"""
        if self._process is None:
            return
        try:
            if self._process.stdin:
                try:
                    self._process.stdin.close()
                except Exception:
                    pass
            self._process.kill()
            self._process.wait(timeout=5)
            logger.info("Node.js Agent 子进程已终止并回收资源")
        except Exception as exc:
            logger.error("终止 Node.js Agent 进程资源失败: %s", exc)
        finally:
            self._process = None


