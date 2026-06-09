import sqlite3
import json
from typing import Optional, List, Any
from .models import ConversationSession, ConversationRun, ToolInvocationRecord


class SessionRepository:
    """CRUD Operations for conversation_session table."""

    @staticmethod
    def create_session(conn: sqlite3.Connection, session_id: str, timestamp: str) -> None:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO conversation_session (id, title, run_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, None, 0, timestamp, timestamp)
        )
        conn.commit()

    @staticmethod
    def get_session(conn: sqlite3.Connection, session_id: str) -> Optional[ConversationSession]:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, run_count, created_at, updated_at FROM conversation_session WHERE id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return ConversationSession(
            id=row[0],
            title=row[1],
            run_count=row[2],
            created_at=row[3],
            updated_at=row[4]
        )

    @staticmethod
    def update_session(conn: sqlite3.Connection, session_id: str, title: Optional[str], run_count: int, timestamp: str) -> None:
        cursor = conn.cursor()
        if title:
            cursor.execute(
                """
                UPDATE conversation_session
                SET title = ?, run_count = ?, updated_at = ?
                WHERE id = ?
                """,
                (title, run_count, timestamp, session_id)
            )
        else:
            cursor.execute(
                """
                UPDATE conversation_session
                SET run_count = ?, updated_at = ?
                WHERE id = ?
                """,
                (run_count, timestamp, session_id)
            )
        conn.commit()

    @staticmethod
    def get_all_sessions(conn: sqlite3.Connection) -> List[ConversationSession]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, run_count, created_at, updated_at FROM conversation_session ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        return [
            ConversationSession(
                id=row[0],
                title=row[1],
                run_count=row[2],
                created_at=row[3],
                updated_at=row[4]
            )
            for row in rows
        ]

    @staticmethod
    def delete_session(conn: sqlite3.Connection, session_id: str) -> None:
        cursor = conn.cursor()
        # 级联删除子记录
        cursor.execute("DELETE FROM tool_invocation_record WHERE run_id IN (SELECT id FROM conversation_run WHERE session_id = ?)", (session_id,))
        cursor.execute("DELETE FROM conversation_run WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM conversation_session WHERE id = ?", (session_id,))
        conn.commit()


class RunRepository:
    """CRUD Operations for conversation_run table."""

    @staticmethod
    def create_run(conn: sqlite3.Connection, run_id: str, session_id: str, user_content: str, timestamp: str) -> None:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO conversation_run (id, session_id, user_content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, session_id, user_content, timestamp)
        )
        conn.commit()

    @staticmethod
    def update_run(conn: sqlite3.Connection, run_id: str, assistant_content: str, tool_calls_json: Optional[str], status: str) -> None:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE conversation_run
            SET assistant_content = ?, tool_calls_json = ?, status = ?
            WHERE id = ?
            """,
            (assistant_content, tool_calls_json, status, run_id)
        )
        conn.commit()

    @staticmethod
    def get_recent_runs(conn: sqlite3.Connection, session_id: str, limit: int = 5) -> List[ConversationRun]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, session_id, user_content, assistant_content, tool_calls_json, created_at, status
            FROM conversation_run
            WHERE session_id = ? AND status = 'success'
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (session_id, limit)
        )
        rows = cursor.fetchall()
        runs = [
            ConversationRun(
                id=row[0],
                session_id=row[1],
                user_content=row[2],
                assistant_content=row[3],
                tool_calls_json=row[4],
                created_at=row[5],
                status=row[6]
            )
            for row in rows
        ]
        # 刚才取出来是降序（最新在最前），返回时我们需要将其逆序（也就是按时间正序），以便在上下文里按第1轮、第2轮顺序列出
        runs.reverse()
        return runs


class ToolRepository:
    """CRUD Operations for tool_invocation_record table."""

    @staticmethod
    def create_tool_record(
        conn: sqlite3.Connection,
        run_id: str,
        tool_name: str,
        input_str: Optional[str],
        output_str: Optional[str],
        is_error: bool,
        timestamp: str
    ) -> None:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tool_invocation_record (run_id, tool_name, input, output, is_error, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, tool_name, input_str, output_str, 1 if is_error else 0, timestamp)
        )
        conn.commit()
