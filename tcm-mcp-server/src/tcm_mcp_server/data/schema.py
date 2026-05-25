"""Schemas and validation primitives for TCM ingestion."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


Nature = Literal["寒", "热", "温", "凉", "平", "大寒", "大热", "微寒", "微温"]
ReviewStatus = Literal["pending", "approved", "rejected", "needs_review"]

VALID_TASTES = {"酸", "苦", "甘", "辛", "咸", "淡", "涩", "微苦"}
VALID_MERIDIANS = {"心", "肝", "脾", "肺", "肾", "胃", "胆", "大肠", "小肠", "膀胱", "心包", "三焦"}
VALID_UNITS = ("g", "克")


class HerbIngestionRecord(BaseModel):
    """Structured herb record parsed from normalized Markdown."""

    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    aliases: str = ""
    nature: Nature
    taste: str = Field(min_length=1)
    meridian: str = Field(min_length=1)
    effect: str = Field(min_length=1)
    indication: str = Field(min_length=1)
    usage: str = ""
    method: str = ""
    caution: str = ""
    toxicity: str = "无毒"
    source: str = Field(min_length=1)
    source_file: str = Field(min_length=1)
    source_heading: str = Field(min_length=1)
    source_text: str = Field(min_length=1)
    source_hash: str = Field(min_length=64, max_length=64)
    parser_version: str = "herb-md-v1"
    review_status: ReviewStatus = "approved"
    review_note: str = ""

    @field_validator("taste")
    @classmethod
    def validate_taste(cls, value: str) -> str:
        tastes = [part.strip() for part in value.replace("，", "、").split("、") if part.strip()]
        invalid = [taste for taste in tastes if taste not in VALID_TASTES]
        if invalid:
            raise ValueError(f"invalid taste: {','.join(invalid)}")
        return value

    @field_validator("meridian")
    @classmethod
    def validate_meridian(cls, value: str) -> str:
        raw = value.replace("经", "").replace("，", "、")
        meridians = [part.strip() for part in raw.split("、") if part.strip()]
        invalid = [meridian for meridian in meridians if meridian not in VALID_MERIDIANS]
        if invalid:
            raise ValueError(f"invalid meridian: {','.join(invalid)}")
        return value


def validate_dose_text(value: str) -> list[str]:
    """Return review reasons for suspicious dosage text."""
    if not value:
        return []
    normalized = value.replace("－", "-").replace("—", "-")
    if any(unit in normalized for unit in VALID_UNITS):
        return []
    return [f"剂量缺少标准单位: {value}"]


def safety_review_reasons(record: HerbIngestionRecord) -> list[str]:
    """Return reasons that require human review before import."""
    reasons: list[str] = []
    combined = f"{record.caution} {record.toxicity} {record.usage}"
    if record.toxicity and record.toxicity != "无毒":
        reasons.append(f"毒性药物需人工复核: {record.toxicity}")
    if any(term in combined for term in ("十八反", "十九畏", "反", "孕妇", "妊娠", "禁用", "忌用")):
        reasons.append("禁忌或妊娠相关内容需人工复核")
    reasons.extend(validate_dose_text(record.usage))
    return reasons
