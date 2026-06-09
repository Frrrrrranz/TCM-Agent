from __future__ import annotations

import logging
import json
from uuid import uuid4
from datetime import datetime
from typing import Optional, List, Any

from .db import get_connection
from .repository import SessionRepository, RunRepository, ToolRepository
from .models import ConversationSession, ConversationRun

logger = logging.getLogger(__name__)


class SessionMemoryService:
    """
    会话级记忆的核心服务类。
    实现 Fail-Open 策略，写库失败仅记录 Warning 并不中断业务流程。
    """

    @staticmethod
    def get_or_create_session(session_id: Optional[str]) -> str:
        """获取或创建新的会话 ID，并在数据库中注册。"""
        if not session_id or not session_id.strip():
            session_id = str(uuid4())
        
        now = datetime.now().isoformat()
        try:
            with get_connection() as conn:
                SessionRepository.create_session(conn, session_id, now)
        except Exception as exc:
            logger.warning("Session Memory 创建会话失败 (Fail-Open): %s", exc)
        
        return session_id

    @staticmethod
    def build_history_context(session_id: str, limit: int = 5, max_chars: int = 2000) -> str:
        """
        拉取最近最多 limit 轮的成功对话，并构建精炼的摘要文本。
        限制输出总字符数不超过 max_chars，避免耗尽 token 预算。
        """
        try:
            with get_connection() as conn:
                runs = RunRepository.get_recent_runs(conn, session_id, limit=limit)
        except Exception as exc:
            logger.warning("Session Memory 获取历史上下文失败 (Fail-Open): %s", exc)
            return ""

        if not runs:
            return ""

        lines = [f"=== 历史问诊记录（最近{len(runs)}轮）==="]
        for idx, run in enumerate(runs, 1):
            user_text = run.user_content.strip()
            # 截取用户主诉
            if len(user_text) > 150:
                user_text = user_text[:150] + "..."
            
            # 截取助手诊断回复，提取纯文本，防止大工具块污染
            assistant_text = run.assistant_content or "无诊断回复"
            if len(assistant_text) > 250:
                assistant_text = assistant_text[:250] + "..."

            # 提取时间 (提取 YYYY-MM-DD HH:MM)
            try:
                dt_str = run.created_at.split(".")[0].replace("T", " ")[:-3]
            except Exception:
                dt_str = run.created_at

            lines.append(f"[{dt_str} 第{idx}轮] 主诉：{user_text}")
            lines.append(f"  诊断建议：{assistant_text}")

        lines.append("===============================")
        context = "\n".join(lines)

        # 长度截断安全阀
        if len(context) > max_chars:
            context = context[:max_chars] + "\n...[历史记录过长已截断]"
        
        return context

    @staticmethod
    def start_run(session_id: str, user_content: str) -> str:
        """在会话中开启新的一轮对话，返回 request_id。"""
        run_id = str(uuid4())
        now = datetime.now().isoformat()
        try:
            with get_connection() as conn:
                # 确保会话头存在
                SessionRepository.create_session(conn, session_id, now)
                # 插入 pending 的 run
                RunRepository.create_run(conn, run_id, session_id, user_content, now)
        except Exception as exc:
            logger.warning("Session Memory 记录开始轮次失败 (Fail-Open): %s", exc)
        return run_id

    @staticmethod
    def finish_run(run_id: str, session_id: str, assistant_content: str, tool_calls: List[dict[str, Any]]) -> None:
        """本轮对话完结，将助手回复和工具调用序列落库，并更新会话的更新时间与轮次数。"""
        now = datetime.now().isoformat()
        tool_calls_json = None
        if tool_calls:
            try:
                tool_calls_json = json.dumps(tool_calls, ensure_ascii=False)
            except Exception:
                pass

        try:
            with get_connection() as conn:
                # 1. 更新 Run 详情
                RunRepository.update_run(conn, run_id, assistant_content, tool_calls_json, "success")
                
                # 2. 读取当前 session 以获取最新的 run_count
                session = SessionRepository.get_session(conn, session_id)
                new_run_count = (session.run_count + 1) if session else 1
                
                # 3. 更新 session 头
                SessionRepository.update_session(conn, session_id, None, new_run_count, now)
        except Exception as exc:
            logger.warning("Session Memory 归档对话轮次失败 (Fail-Open): %s", exc)

    @staticmethod
    def record_tool_invocation(run_id: str, tool_name: str, tool_input: Any, tool_output: Any, is_error: bool) -> None:
        """记录具体的工具调用细节。"""
        now = datetime.now().isoformat()
        input_str = None
        output_str = None
        try:
            if tool_input is not None:
                input_str = json.dumps(tool_input, ensure_ascii=False) if not isinstance(tool_input, str) else tool_input
            if tool_output is not None:
                output_str = json.dumps(tool_output, ensure_ascii=False) if not isinstance(tool_output, str) else tool_output
        except Exception:
            pass

        try:
            with get_connection() as conn:
                ToolRepository.create_tool_record(conn, run_id, tool_name, input_str, output_str, is_error, now)
        except Exception as exc:
            logger.warning("Session Memory 归档工具详情失败 (Fail-Open): %s", exc)
