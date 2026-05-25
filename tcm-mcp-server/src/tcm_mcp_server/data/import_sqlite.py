"""Safe SQLite import entrypoints for validated ingestion records."""

from __future__ import annotations

from pathlib import Path

from .database import Database
from .parse_herbs import parse_herb_file
from .review_queue import enqueue_review
from .schema import HerbIngestionRecord
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


def import_herb_file(db: Database, path: str | Path, review_dir: str | Path) -> bool:
    """Parse and import one normalized herb Markdown file."""
    record = parse_herb_file(path)
    return import_herb_record(db, record, review_dir)
