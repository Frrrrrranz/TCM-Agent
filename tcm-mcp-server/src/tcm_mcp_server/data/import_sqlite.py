"""Safe SQLite import entrypoints for validated ingestion records."""

from __future__ import annotations

from pathlib import Path

from .database import Database
from .review_queue import enqueue_review, enqueue_prescription_review
from .schema import HerbIngestionRecord, PrescriptionIngestionRecord
from .validate_records import validate_herb_record


def herb_record_to_db_dict(record: HerbIngestionRecord) -> dict:
    """Convert an ingestion schema into Database.insert_herb input."""
    data = record.model_dump()
    data["pinyin"] = data.get("pinyin", "")
    return data


def import_herb_record(
    db: Database,
    record: HerbIngestionRecord,
    review_dir: str | Path,
) -> bool:
    """Import a herb if it passes validation; otherwise enqueue for review."""
    result = validate_herb_record(record)
    if not result.approved:
        enqueue_review(result, review_dir)
        return False

    db.insert_herb(herb_record_to_db_dict(record))
    return True


def import_prescription_record(
    db: Database,
    record: PrescriptionIngestionRecord,
    review_dir: str | Path,
) -> bool:
    """Import a prescription record (with basic existence check)."""
    data = record.model_dump()

    # 检查是否已存在同名记录（name 列有 UNIQUE 约束）
    existing = db.get_prescription_by_name(data["name"])
    if existing:
        # 如果已存在且 source 不同，写入 review 队列人工判断
        if existing.source != data.get("source", ""):
            from .review_queue import enqueue_prescription_review
            enqueue_prescription_review(record, review_dir)
            return False
        return True  # 相同 source 的重复数据，直接跳过

    db.insert_prescription(data)
    return True


def import_prescription_record_batch(
    db: Database,
    records: list[PrescriptionIngestionRecord],
    review_dir: str | Path,
) -> dict[str, int]:
    """批量导入方剂记录，返回统计。"""
    counts: dict[str, int] = {"imported": 0, "skipped": 0, "reviewed": 0, "errors": 0}

    for record in records:
        try:
            if import_prescription_record(db, record, review_dir):
                counts["imported"] += 1
            else:
                counts["skipped"] += 1
        except Exception:
            counts["errors"] += 1

    return counts


def import_herb_file(
    db: Database,
    file_path: str | Path,
    review_dir: str | Path,
) -> bool:
    """Read a markdown file, parse it, and import it to database or review queue."""
    from .normalize_markdown import normalize_text
    from .parse_herbs import parse_herb_markdown

    path = Path(file_path)
    content = path.read_text(encoding="utf-8")
    normalized = normalize_text(content)
    record = parse_herb_markdown(normalized, source_file=path.name)
    if not record:
        return False
    return import_herb_record(db, record, review_dir)