"""Validation gate for parsed TCM ingestion records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from .schema import HerbIngestionRecord, PrescriptionIngestionRecord, safety_review_reasons

RecordT = TypeVar("RecordT", HerbIngestionRecord, PrescriptionIngestionRecord)


@dataclass(frozen=True)
class ValidationResult(Generic[RecordT]):
    approved: bool
    reasons: list[str]
    record: RecordT


def validate_herb_record(record: HerbIngestionRecord) -> ValidationResult[HerbIngestionRecord]:
    """Validate one herb record and decide whether it can enter SQLite."""
    reasons: list[str] = []

    required_fields = {
        "name": record.name,
        "category": record.category,
        "nature": record.nature,
        "taste": record.taste,
        "meridian": record.meridian,
        "effect": record.effect,
        "indication": record.indication,
        "source": record.source,
        "source_text": record.source_text,
        "source_hash": record.source_hash,
    }
    missing = [field for field, value in required_fields.items() if not value]
    if missing:
        reasons.append(f"必填字段缺失: {', '.join(missing)}")

    reasons.extend(safety_review_reasons(record))
    return ValidationResult(approved=not reasons, reasons=reasons, record=record)


def validate_prescription_record(
    record: PrescriptionIngestionRecord,
) -> ValidationResult[PrescriptionIngestionRecord]:
    """Validate one prescription record and decide whether it can enter SQLite."""
    reasons: list[str] = []

    required_fields = {
        "name": record.name,
        "composition": record.composition,
        "source": record.source,
        "source_hash": record.source_hash,
    }
    missing = [field for field, value in required_fields.items() if not value]
    if missing:
        reasons.append(f"必填字段缺失: {', '.join(missing)}")

    # 方剂安全审查：检查组成中是否含毒性药物
    if record.composition:
        toxic_indicators = (
            "乌头",
            "附子",
            "巴豆",
            "甘遂",
            "大戟",
            "芫花",
            "马钱子",
            "细辛",
            "雄黄",
            "朱砂",
        )
        found_toxic = [h for h in record.composition.split(", ") if h in toxic_indicators]
        if found_toxic:
            reasons.append(f"含毒性药物需人工复核: {', '.join(found_toxic)}")

    return ValidationResult(approved=not reasons, reasons=reasons, record=record)
