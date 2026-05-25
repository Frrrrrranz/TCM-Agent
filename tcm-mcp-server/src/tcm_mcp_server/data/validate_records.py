"""Validation gate for parsed TCM ingestion records."""

from __future__ import annotations

from dataclasses import dataclass

from .schema import HerbIngestionRecord, safety_review_reasons


@dataclass(frozen=True)
class ValidationResult:
    approved: bool
    reasons: list[str]
    record: HerbIngestionRecord


def validate_herb_record(record: HerbIngestionRecord) -> ValidationResult:
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
