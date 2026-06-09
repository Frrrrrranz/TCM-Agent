"""Review queue writer for records that fail ingestion gates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import HerbIngestionRecord, PrescriptionIngestionRecord
from .validate_records import ValidationResult


def enqueue_review(result: ValidationResult, review_dir: str | Path) -> Path:
    """Write a failed validation result as JSON for human review."""
    path = Path(review_dir)
    path.mkdir(parents=True, exist_ok=True)
    target = path / f"{result.record.source_hash}.json"
    payload = {
        "name": result.record.name,
        "review_status": "needs_review",
        "review_reasons": result.reasons,
        "record": result.record.model_dump(),
    }
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


def enqueue_prescription_review(record: PrescriptionIngestionRecord, review_dir: str | Path) -> Path:
    """Write a prescription record with conflicts (e.g. duplicate name, different source) for review."""
    path = Path(review_dir)
    path.mkdir(parents=True, exist_ok=True)
    source_hash = record.source_hash
    target = path / f"{source_hash}_prescription.json"
    payload: dict[str, Any] = {
        "name": record.name,
        "review_status": "needs_review",
        "review_reasons": ["同名方剂来自不同数据源，需要人工合并"],
        "record": record.model_dump(),
    }
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target
