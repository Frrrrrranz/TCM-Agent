import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)

def get_db_path() -> Path:
    # 位于 src/tcm_mcp_server/web/memory/db.py
    # 往上数 4 级：memory -> web -> tcm_mcp_server -> src -> tcm-mcp-server
    base_dir = Path(__file__).resolve().parents[4]
    data_dir = base_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "memory.db"

DB_PATH = get_db_path()

def init_db() -> None:
    """初始化 SQLite 数据库 Schema。"""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # 1. 会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_session (
                id TEXT PRIMARY KEY,
                title TEXT,
                run_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # 2. 单次问诊表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_run (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_content TEXT,
                assistant_content TEXT,
                tool_calls_json TEXT,
                created_at TEXT NOT NULL,
                status TEXT DEFAULT 'success',
                FOREIGN KEY(session_id) REFERENCES conversation_session(id)
            )
        """)
        
        # 3. 工具调用明细表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_invocation_record (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                input TEXT,
                output TEXT,
                is_error INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES conversation_run(id)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Session Memory 数据库初始化成功: %s", DB_PATH)
    except Exception as exc:
        logger.error("Session Memory 数据库初始化失败: %s", exc, exc_info=True)

@contextmanager
def get_connection():
    """获取数据库连接的上下文管理器。"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()
