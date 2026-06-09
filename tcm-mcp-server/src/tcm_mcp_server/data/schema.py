"""Schemas and validation primitives for TCM ingestion."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


Nature = Literal["寒", "热", "温", "凉", "平", "大寒", "大热", "微寒", "微温"]
ReviewStatus = Literal["pending", "approved", "rejected", "needs_review"]

VALID_TASTES = {"酸", "苦", "甘", "辛", "咸", "淡", "涩", "微苦"}
VALID_MERIDIANS = {"心", "肝", "脾", "肺", "肾", "胃", "胆", "大肠", "小肠", "膀胱", "心包", "三焦"}
VALID_UNITS = ("g", "克")

# ── 英文 TCM 属性 → 中文标准值 映射 ──────────────────────
# HERB / TCMbank 数据源中的属性字段多为英文，需翻译后再校验

TCM_PROPERTY_MAP: dict[str, str] = {
    # 四气（Nature）—— 标准
    "cold": "寒",
    "hot": "热",
    "warm": "温",
    "cool": "凉",
    "neutral": "平",
    "great cold": "大寒",
    "great hot": "大热",
    "slightly cold": "微寒",
    "slightly warm": "微温",
    # 四气（Nature）—— 变体，来自 HERB 数据库
    "mild": "平",
    "minor warm": "微温",
    "minor cold": "微寒",
    "slightly warm": "微温",
    "slightly cold": "微寒",
    "extreme cold": "大寒",
    "extremely cold": "大寒",
    "extreme hot": "大热",
    "extreme warm": "温",
    "slightly sweet": "甘",
    "slightly pungent": "辛",
    "slightly sour": "酸",
    "minor cool": "凉",
    "punkery": "平",
    # 四气（Nature）—— 中文恒等（原始数据中可能已是中文）
    "寒": "寒",
    "热": "热",
    "温": "温",
    "凉": "凉",
    "平": "平",
    "大寒": "大寒",
    "大热": "大热",
    "微寒": "微寒",
    "微温": "微温",
    # 五味（Taste）—— 标准
    "sour": "酸",
    "bitter": "苦",
    "sweet": "甘",
    "acrid": "辛",
    "pungent": "辛",
    "salty": "咸",
    "light": "淡",
    "astringent": "涩",
    "slightly bitter": "微苦",
    # 五味（Taste）—— 首字母大写变体
    "Sour": "酸",
    "Bitter": "苦",
    "Sweet": "甘",
    "Acrid": "辛",
    "Pungent": "辛",
    "Salty": "咸",
    "Light": "淡",
    "Astringent": "涩",
    # 允许含分号的复合值（如 "Warm; Sour"）
}

MERIDIAN_MAP: dict[str, str] = {
    "heart": "心",
    "liver": "肝",
    "spleen": "脾",
    "lung": "肺",
    "kidney": "肾",
    "stomach": "胃",
    "gallbladder": "胆",
    "large intestine": "大肠",
    "small intestine": "小肠",
    "bladder": "膀胱",
    "pericardium": "心包",
    "triple energizer": "三焦",
    "san jiao": "三焦",
    "cardiovascular": "心",
    "three end": "三焦",
}


def translate_property(en_value: str | None) -> str:
    """将英文 TCM 属性值翻译为中文标准值，若无法识别则原样返回。

    支持 ";" 分隔的复合值，例如 "Warm; Sour" → "温；酸"
    """
    if not en_value or en_value.strip() in ("NA", "", "None"):
        return ""
    parts = en_value.replace("；", ";").replace(",", ";").replace("，", ";").split(";")
    translated: list[str] = []
    for part in parts:
        part = part.strip()
        key = part.lower()
        if key in TCM_PROPERTY_MAP:
            translated.append(TCM_PROPERTY_MAP[key])
        else:
            # 保持原样，不中断解析
            translated.append(part)
    return "；".join(translated)


def translate_meridian(en_value: str | None) -> str:
    """将英文归经值翻译为中文标准值。"""
    if not en_value or en_value.strip() in ("NA", "", "None"):
        return ""
    parts = en_value.replace(",", ";").replace("，", ";").replace("；", ";").split(";")
    translated: list[str] = []
    for part in parts:
        part = part.strip()
        key = part.lower()
        if key in MERIDIAN_MAP:
            translated.append(MERIDIAN_MAP[key])
        else:
            translated.append(part)
    return "、".join(translated)


class HerbIngestionRecord(BaseModel):
    """Structured herb record parsed from normalized Markdown."""

    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    aliases: str = ""
    nature: Nature
    taste: str = Field(min_length=1)
    meridian: str = Field(min_length=1)
    effect: str = ""
    indication: str = ""
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


class PrescriptionIngestionRecord(BaseModel):
    """Structured prescription record parsed from xlsx / normalized data."""

    name: str = Field(min_length=1)
    source: str = Field(min_length=1)
    category: str = ""
    composition: str = Field(min_length=1)
    effect: str = ""
    indication: str = ""
    syndrome: str = ""
    symptoms: str = ""
    usage: str = ""
    caution: str = ""
    source_file: str = Field(min_length=1)
    source_heading: str = Field(min_length=1)
    source_text: str = ""
    source_hash: str = Field(min_length=64, max_length=64)
    parser_version: str = "formula-xlsx-v1"
    review_status: ReviewStatus = "approved"
    review_note: str = ""


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