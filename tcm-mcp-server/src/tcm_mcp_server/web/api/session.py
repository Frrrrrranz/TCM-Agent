from __future__ import annotations

import logging
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from ..memory.db import get_connection
from ..memory.repository import SessionRepository
from ..memory.models import ConversationSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionResponse(BaseModel):
    id: str
    title: Optional[str] = None
    runCount: int
    createdAt: str
    updatedAt: str

    class Config:
        populate_by_name = True


@router.get("", response_model=List[SessionResponse])
async def list_sessions() -> List[SessionResponse]:
    """获取所有历史问诊会话列表。"""
    try:
        sessions = await asyncio.to_thread(
            lambda: [
                SessionResponse(
                    id=s.id,
                    title=s.title,
                    runCount=s.run_count,
                    createdAt=s.created_at,
                    updatedAt=s.updated_at
                )
                for s in get_connection_and_list()
            ]
        )
        return sessions
    except Exception as exc:
        logger.exception("获取会话列表异常")
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(exc)}")


def get_connection_and_list() -> List[ConversationSession]:
    with get_connection() as conn:
        return SessionRepository.get_all_sessions(conn)


@router.delete("/{session_id}")
async def delete_session(session_id: str) -> dict[str, str]:
    """删除指定的问诊会话。"""
    try:
        await asyncio.to_thread(delete_session_sync, session_id)
        return {"status": "ok", "message": f"Session {session_id} has been deleted."}
    except Exception as exc:
        logger.exception("删除会话异常: %s", session_id)
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(exc)}")


def delete_session_sync(session_id: str) -> None:
    with get_connection() as conn:
        SessionRepository.delete_session(conn, session_id)
