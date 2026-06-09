"""
SQLite 数据库封装层。

提供中医药结构化数据的 CRUD 操作，支持精确查询与模糊匹配。
"""

from __future__ import annotations

import sqlite3
import logging
from hashlib import sha256
from pathlib import Path
from typing import Optional

from ..models.herb import Herb, HerbSearchParams
from ..models.prescription import Prescription, PrescriptionSearchParams
from ..models.syndrome import Syndrome, SyndromeSearchParams
from ..models.acupoint import Acupoint, AcupointSearchParams

logger = logging.getLogger(__name__)


class Database:
    """SQLite 数据库封装，提供中医药数据的精确查询能力。"""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        """建立数据库连接并初始化表结构。"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        self._conn.row_factory = sqlite3.Row
        self._init_tables()
        logger.info("数据库已连接: %s", self.db_path)

    def close(self) -> None:
        """关闭数据库连接。"""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("数据库连接已关闭")

    @property
    def conn(self) -> sqlite3.Connection:
        """获取数据库连接，自动重连。"""
        if self._conn is None:
            self.connect()
        return self._conn

    # ── 表初始化 ──────────────────────────────────────────────

    def _init_tables(self) -> None:
        """创建所有必要的数据库表。"""
        cursor = self.conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS herbs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                pinyin TEXT DEFAULT '',
                category TEXT DEFAULT '',
                nature TEXT DEFAULT '平',
                taste TEXT DEFAULT '甘',
                meridian TEXT DEFAULT '',
                toxicity TEXT DEFAULT '无毒',
                effect TEXT DEFAULT '',
                indication TEXT DEFAULT '',
                usage TEXT DEFAULT '',
                caution TEXT DEFAULT '',
                source TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS prescriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                source TEXT DEFAULT '',
                category TEXT DEFAULT '',
                composition TEXT DEFAULT '',
                effect TEXT DEFAULT '',
                indication TEXT DEFAULT '',
                syndrome TEXT DEFAULT '',
                symptoms TEXT DEFAULT '',
                explanation TEXT DEFAULT '',
                addition TEXT DEFAULT '',
                caution TEXT DEFAULT '',
                source_text TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS syndromes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT DEFAULT '',
                key_symptoms TEXT DEFAULT '',
                tongue TEXT DEFAULT '',
                pulse TEXT DEFAULT '',
                mechanism TEXT DEFAULT '',
                treatment_principle TEXT DEFAULT '',
                source TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS acupoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                pinyin TEXT DEFAULT '',
                meridian TEXT DEFAULT '',
                location TEXT DEFAULT '',
                indication TEXT DEFAULT '',
                operation TEXT DEFAULT '',
                caution TEXT DEFAULT '',
                source TEXT DEFAULT ''
            );

            -- 创建常用索引
            CREATE INDEX IF NOT EXISTS idx_herbs_category ON herbs(category);
            CREATE INDEX IF NOT EXISTS idx_herbs_nature ON herbs(nature);
            CREATE INDEX IF NOT EXISTS idx_prescriptions_category ON prescriptions(category);
            CREATE INDEX IF NOT EXISTS idx_syndromes_category ON syndromes(category);
            CREATE INDEX IF NOT EXISTS idx_acupoints_meridian ON acupoints(meridian);
        """)

        self._ensure_traceability_columns(cursor)
        self._backfill_traceability_defaults(cursor)
        self.conn.commit()

    def _ensure_traceability_columns(self, cursor: sqlite3.Cursor) -> None:
        """Add traceability columns to databases created before this schema."""
        columns = {
            "source_file": "TEXT DEFAULT ''",
            "source_heading": "TEXT DEFAULT ''",
            "source_text": "TEXT DEFAULT ''",
            "source_hash": "TEXT DEFAULT ''",
            "parser_version": "TEXT DEFAULT 'seed-v1'",
            "review_status": "TEXT DEFAULT 'approved'",
            "review_note": "TEXT DEFAULT ''",
        }

        for table in ("herbs", "prescriptions", "syndromes", "acupoints"):
            existing = {
                row["name"]
                for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()
            }
            for name, definition in columns.items():
                if name not in existing:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    @staticmethod
    def _source_hash(data: dict, fallback: str) -> str:
        source_text = data.get("source_text") or fallback
        return data.get("source_hash") or sha256(source_text.encode("utf-8")).hexdigest()

    def _backfill_traceability_defaults(self, cursor: sqlite3.Cursor) -> None:
        """Populate traceability defaults for rows created before trace fields existed."""
        table_sources = {
            "herbs": "seed_herbs.py",
            "prescriptions": "seed_prescriptions.py",
            "syndromes": "seed_syndromes.py",
            "acupoints": "seed_acupoints.py",
        }

        for table, source_file in table_sources.items():
            rows = cursor.execute(
                f"""
                SELECT id, name, source, source_text
                FROM {table}
                WHERE source_hash = '' OR source_heading = '' OR source_file = ''
                """
            ).fetchall()
            for row in rows:
                source_text = row["source_text"] or row["source"] or row["name"]
                source_hash = sha256(source_text.encode("utf-8")).hexdigest()
                cursor.execute(
                    f"""
                    UPDATE {table}
                    SET source_file = COALESCE(NULLIF(source_file, ''), ?),
                        source_heading = COALESCE(NULLIF(source_heading, ''), ?),
                        source_text = COALESCE(NULLIF(source_text, ''), ?),
                        source_hash = COALESCE(NULLIF(source_hash, ''), ?),
                        parser_version = COALESCE(NULLIF(parser_version, ''), 'seed-v1'),
                        review_status = COALESCE(NULLIF(review_status, ''), 'approved')
                    WHERE id = ?
                    """,
                    (source_file, row["name"], source_text, source_hash, row["id"]),
                )

    # ── 中药查询 ──────────────────────────────────────────────

    def search_herbs(self, params: HerbSearchParams) -> list[Herb]:
        """查询中药，支持按名称精确匹配和按属性筛选。"""
        query = "SELECT * FROM herbs WHERE 1=1"
        bindings: list = []

        if params.name:
            query += " AND name = ?"
            bindings.append(params.name)
        if params.nature:
            query += " AND nature LIKE ?"
            bindings.append(f"%{params.nature}%")
        if params.taste:
            query += " AND taste LIKE ?"
            bindings.append(f"%{params.taste}%")
        if params.meridian:
            query += " AND meridian LIKE ?"
            bindings.append(f"%{params.meridian}%")
        if params.keywords:
            # 关键词在名称、功效、主治中模糊搜索
            query += " AND (name LIKE ? OR effect LIKE ? OR indication LIKE ? OR pinyin LIKE ?)"
            kw = f"%{params.keywords}%"
            bindings.extend([kw, kw, kw, kw])

        query += " ORDER BY name LIMIT 20"
        cursor = self.conn.execute(query, bindings)
        return [Herb(**dict(row)) for row in cursor.fetchall()]

    def get_herb_by_name(self, name: str) -> Optional[Herb]:
        """按名称精确获取中药。"""
        cursor = self.conn.execute("SELECT * FROM herbs WHERE name = ?", (name,))
        row = cursor.fetchone()
        return Herb(**dict(row)) if row else None

    def insert_herb(self, data: dict) -> int:
        """插入一条中药记录。"""
        cursor = self.conn.execute("""
            INSERT OR REPLACE INTO herbs
                (name, pinyin, category, nature, taste, meridian, toxicity,
                 effect, indication, usage, caution, source, source_file,
                 source_heading, source_text, source_hash, parser_version,
                 review_status, review_note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["name"], data.get("pinyin", ""), data.get("category", ""),
            data.get("nature", "平"), data.get("taste", "甘"),
            data.get("meridian", ""), data.get("toxicity", "无毒"),
            data.get("effect", ""), data.get("indication", ""),
            data.get("usage", ""), data.get("caution", ""), data.get("source", ""),
            data.get("source_file", "seed_herbs.py"),
            data.get("source_heading", data["name"]),
            data.get("source_text", data.get("source", "")),
            self._source_hash(data, f"{data['name']}|{data.get('source', '')}"),
            data.get("parser_version", "seed-v1"),
            data.get("review_status", "approved"),
            data.get("review_note", ""),
        ))
        self.conn.commit()
        return cursor.lastrowid

    # ── 方剂查询 ──────────────────────────────────────────────

    def search_prescriptions(self, params: PrescriptionSearchParams) -> list[Prescription]:
        """查询方剂，支持按名称、证型、症状搜索。"""
        query = "SELECT * FROM prescriptions WHERE 1=1"
        bindings: list = []

        if params.name:
            query += " AND name = ?"
            bindings.append(params.name)
        if params.syndrome:
            query += " AND syndrome LIKE ?"
            bindings.append(f"%{params.syndrome}%")
        if params.symptoms:
            query += " AND (symptoms LIKE ? OR indication LIKE ?)"
            kw = f"%{params.symptoms}%"
            bindings.extend([kw, kw])
        if params.herbs:
            # 方剂组成中包含指定药物
            for herb in params.herbs.split(","):
                herb = herb.strip()
                if herb:
                    query += " AND composition LIKE ?"
                    bindings.append(f"%{herb}%")

        query += " ORDER BY name LIMIT 20"
        cursor = self.conn.execute(query, bindings)
        return [Prescription(**dict(row)) for row in cursor.fetchall()]

    def get_prescription_by_name(self, name: str) -> Optional[Prescription]:
        """按名称精确获取方剂。"""
        cursor = self.conn.execute("SELECT * FROM prescriptions WHERE name = ?", (name,))
        row = cursor.fetchone()
        return Prescription(**dict(row)) if row else None

    def insert_prescription(self, data: dict) -> int:
        """插入一条方剂记录。"""
        cursor = self.conn.execute("""
            INSERT OR REPLACE INTO prescriptions
                (name, source, category, composition, effect, indication,
                 syndrome, symptoms, explanation, addition, caution, source_text,
                 source_file, source_heading, source_hash, parser_version,
                 review_status, review_note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["name"], data.get("source", ""), data.get("category", ""),
            data.get("composition", ""), data.get("effect", ""),
            data.get("indication", ""), data.get("syndrome", ""),
            data.get("symptoms", ""), data.get("explanation", ""),
            data.get("addition", ""), data.get("caution", ""),
            data.get("source_text", ""),
            data.get("source_file", "seed_prescriptions.py"),
            data.get("source_heading", data["name"]),
            self._source_hash(
                data,
                f"{data['name']}|{data.get('source_text', data.get('source', ''))}",
            ),
            data.get("parser_version", "seed-v1"),
            data.get("review_status", "approved"),
            data.get("review_note", ""),
        ))
        self.conn.commit()
        return cursor.lastrowid

    # ── 证型查询 ──────────────────────────────────────────────

    def search_syndromes(self, params: SyndromeSearchParams) -> list[Syndrome]:
        """查询证型。"""
        query = "SELECT * FROM syndromes WHERE 1=1"
        bindings: list = []

        if params.name:
            query += " AND name = ?"
            bindings.append(params.name)
        if params.category:
            query += " AND category LIKE ?"
            bindings.append(f"%{params.category}%")
        if params.symptoms:
            query += " AND key_symptoms LIKE ?"
            bindings.append(f"%{params.symptoms}%")

        query += " ORDER BY name LIMIT 20"
        cursor = self.conn.execute(query, bindings)
        return [Syndrome(**dict(row)) for row in cursor.fetchall()]

    def insert_syndrome(self, data: dict) -> int:
        """插入一条证型记录。"""
        cursor = self.conn.execute("""
            INSERT OR REPLACE INTO syndromes
                (name, category, key_symptoms, tongue, pulse,
                 mechanism, treatment_principle, source, source_file,
                 source_heading, source_text, source_hash, parser_version,
                 review_status, review_note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["name"], data.get("category", ""), data.get("key_symptoms", ""),
            data.get("tongue", ""), data.get("pulse", ""),
            data.get("mechanism", ""), data.get("treatment_principle", ""),
            data.get("source", ""),
            data.get("source_file", "seed_syndromes.py"),
            data.get("source_heading", data["name"]),
            data.get("source_text", data.get("source", "")),
            self._source_hash(data, f"{data['name']}|{data.get('source', '')}"),
            data.get("parser_version", "seed-v1"),
            data.get("review_status", "approved"),
            data.get("review_note", ""),
        ))
        self.conn.commit()
        return cursor.lastrowid

    # ── 穴位查询 ──────────────────────────────────────────────

    def search_acupoints(self, params: AcupointSearchParams) -> list[Acupoint]:
        """查询穴位。"""
        query = "SELECT * FROM acupoints WHERE 1=1"
        bindings: list = []

        if params.name:
            query += " AND name = ?"
            bindings.append(params.name)
        if params.meridian:
            query += " AND meridian LIKE ?"
            bindings.append(f"%{params.meridian}%")
        if params.keywords:
            query += " AND (name LIKE ? OR location LIKE ? OR indication LIKE ?)"
            kw = f"%{params.keywords}%"
            bindings.extend([kw, kw, kw])

        query += " ORDER BY name LIMIT 20"
        cursor = self.conn.execute(query, bindings)
        return [Acupoint(**dict(row)) for row in cursor.fetchall()]

    def insert_acupoint(self, data: dict) -> int:
        """插入一条穴位记录。"""
        cursor = self.conn.execute("""
            INSERT OR REPLACE INTO acupoints
                (name, pinyin, meridian, location, indication, operation, caution, source,
                 source_file, source_heading, source_text, source_hash, parser_version,
                 review_status, review_note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["name"], data.get("pinyin", ""), data.get("meridian", ""),
            data.get("location", ""), data.get("indication", ""),
            data.get("operation", ""), data.get("caution", ""),
            data.get("source", ""),
            data.get("source_file", "seed_acupoints.py"),
            data.get("source_heading", data["name"]),
            data.get("source_text", data.get("source", "")),
            self._source_hash(data, f"{data['name']}|{data.get('source', '')}"),
            data.get("parser_version", "seed-v1"),
            data.get("review_status", "approved"),
            data.get("review_note", ""),
        ))
        self.conn.commit()
        return cursor.lastrowid

    # ── 配伍禁忌检查 ──────────────────────────────────────────

    # 十八反经典配伍
    EIGHTEEN_ANTI_PAIRS: list[tuple[str, str]] = [
        ("乌头", "半夏"), ("乌头", "瓜蒌"), ("乌头", "贝母"),
        ("乌头", "白蔹"), ("乌头", "白及"),
        ("甘草", "海藻"), ("甘草", "大戟"), ("甘草", "甘遂"), ("甘草", "芫花"),
        ("藜芦", "人参"), ("藜芦", "沙参"), ("藜芦", "丹参"),
        ("藜芦", "玄参"), ("藜芦", "苦参"), ("藜芦", "细辛"), ("藜芦", "芍药"),
    ]

    HERB_ALIASES: dict[str, tuple[str, ...]] = {
        "乌头": ("乌头", "川乌", "草乌", "附子", "制川乌", "制草乌"),
        "贝母": ("贝母", "川贝母", "浙贝母"),
        "瓜蒌": ("瓜蒌", "全瓜蒌", "瓜蒌皮", "瓜蒌仁", "天花粉"),
        "芍药": ("芍药", "白芍", "赤芍"),
        "沙参": ("沙参", "南沙参", "北沙参"),
        "大戟": ("大戟", "京大戟", "红大戟"),
        "朴硝": ("朴硝", "芒硝", "玄明粉"),
        "砒霜": ("砒霜", "砒石"),
        "牵牛": ("牵牛", "牵牛子", "黑丑", "白丑"),
        "官桂": ("官桂", "肉桂", "桂枝"),
        "犀角": ("犀角", "水牛角"),
    }

    # 十九畏经典配伍
    NINETEEN_FEAR_PAIRS: list[tuple[str, str]] = [
        ("硫黄", "朴硝"), ("水银", "砒霜"), ("狼毒", "密陀僧"),
        ("巴豆", "牵牛"), ("丁香", "郁金"), ("牙硝", "三棱"),
        ("川乌", "犀角"), ("人参", "五灵脂"), ("官桂", "赤石脂"),
    ]

    def check_drug_interaction(self, herbs: list[str]) -> list[dict]:
        """
        检查药物配伍禁忌。

        返回包含冲突药物对和原因说明的列表。
        """
        conflicts: list[dict] = []
        herb_set = {herb.strip() for herb in herbs if herb.strip()}

        def present(canonical: str) -> str | None:
            for alias in self.HERB_ALIASES.get(canonical, (canonical,)):
                if alias in herb_set:
                    return alias
            return None

        # 检查十八反
        for herb_a, herb_b in self.EIGHTEEN_ANTI_PAIRS:
            matched_a = present(herb_a)
            matched_b = present(herb_b)
            if matched_a and matched_b:
                conflicts.append({
                    "type": "十八反",
                    "herb_a": matched_a,
                    "herb_b": matched_b,
                    "description": f"{matched_a}与{matched_b}相反，属十八反禁忌",
                    "severity": "error",
                })

        # 检查十九畏
        for herb_a, herb_b in self.NINETEEN_FEAR_PAIRS:
            matched_a = present(herb_a)
            matched_b = present(herb_b)
            if matched_a and matched_b:
                conflicts.append({
                    "type": "十九畏",
                    "herb_a": matched_a,
                    "herb_b": matched_b,
                    "description": f"{matched_a}与{matched_b}相畏，属十九畏禁忌",
                    "severity": "warning",
                })

        # 检查毒性药物
        toxic_herbs = self._get_toxic_herbs(herbs)
        conflicts.extend(toxic_herbs)

        return conflicts

    def _get_toxic_herbs(self, herbs: list[str]) -> list[dict]:
        """检查是否有毒性药物。"""
        warnings: list[dict] = []
        for herb_name in herbs:
            herb = self.get_herb_by_name(herb_name)
            if herb and herb.toxicity and herb.toxicity != "无毒":
                warnings.append({
                    "type": "毒性药物",
                    "herb_a": herb_name,
                    "herb_b": "",
                    "description": f"{herb_name}标记为{herb.toxicity}，需谨慎使用",
                    "severity": "warning",
                })
        return warnings
