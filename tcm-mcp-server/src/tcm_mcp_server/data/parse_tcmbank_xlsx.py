"""Deterministic parser for TCMbank xlsx exports."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .schema import (
    HerbIngestionRecord,
    VALID_TASTES,
    translate_property,
    translate_meridian,
)

NATURE_CHINESE = frozenset({"寒", "热", "温", "凉", "平", "大寒", "大热", "微寒", "微温"})


def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if s in ("NA", "NaN", "None", ""):
        return ""
    return s


def parse_tcmbank_herb_row(row: dict[str, Any], source_file: str) -> HerbIngestionRecord | None:
    """Parse one row from TCMbank bank-herbs.xlsx or herb_all.xlsx.

    Primary columns (bank-herbs.xlsx):
      - TCM_name          → name
      - Properties        → nature (English, translated)
      - Meridians         → meridian (English, translated)
      - Function          → effect
      - Indication        → indication
      - Toxicity          → toxicity
      - UsePart           → category
      - Therapeutic_cn_class → category fallback

    Also handles herb_all.xlsx with more columns.
    """
    name = _normalize_value(row.get("TCM_name", ""))
    if not name:
        return None

    raw_properties = _normalize_value(row.get("Properties", ""))
    raw_meridian = _normalize_value(row.get("Meridians", ""))
    effect = _normalize_value(row.get("Function", "")) or "未收录"
    indication = _normalize_value(row.get("Indication", "")) or "未收录"
    toxicity = _normalize_value(row.get("Toxicity", ""))
    use_part = _normalize_value(row.get("UsePart", ""))
    therapeutic = _normalize_value(row.get("Therapeutic_cn_class", ""))
    source = "TCMbank"

    # 分类：UsePart > Therapeutic_cn_class
    category = use_part or therapeutic
    if not category:
        category = "未分类"

    # 收集并智能分拣属性分词（性、味）
    nature_parts = []
    taste_parts = []

    all_properties = []
    if raw_properties:
        all_properties.extend(translate_property(raw_properties).replace("；", ";").replace(",", ";").replace("，", ";").split(";"))

    for part in all_properties:
        part = part.strip()
        if not part:
            continue
        if part in NATURE_CHINESE:
            nature_parts.append(part)
        elif part in VALID_TASTES:
            taste_parts.append(part)
        else:
            taste_parts.append(part)

    nature = nature_parts[0] if nature_parts else "平"

    seen_tastes = []
    for t in taste_parts:
        if t not in seen_tastes:
            seen_tastes.append(t)
    taste = "、".join(seen_tastes) if seen_tastes else "甘"

    meridian = translate_meridian(raw_meridian) if raw_meridian else "肝"

    source_text_lines = [
        f"名称: {name}",
        f"分类: {category}",
        f"归经: {raw_meridian}",
        f"功效: {effect}",
        f"主治: {indication}",
    ]
    source_text = "\n".join(l for l in source_text_lines if l)

    payload = {
        "name": name,
        "category": category,
        "nature": nature,
        "taste": taste,
        "meridian": meridian,
        "effect": effect,
        "indication": indication,
        "toxicity": toxicity or "无毒",
        "source": source,
        "source_file": source_file,
        "source_heading": name,
        "source_text": source_text or name,
        "source_hash": sha256(source_text.encode("utf-8")).hexdigest() if source_text else sha256(name.encode("utf-8")).hexdigest(),
        "parser_version": "tcmbank-xlsx-v1",
    }

    try:
        return HerbIngestionRecord(**payload)
    except ValidationError as exc:
        raise ValueError(f"TCMbank 行校验失败 ({name}): {exc}") from exc


def parse_tcmbank_xlsx(path: str | Path) -> list[HerbIngestionRecord]:
    """Parse all rows from a TCMbank xlsx file (bank-herbs.xlsx or herb_all.xlsx)."""
    import openpyxl  # lazy import

    file_path = Path(path)
    wb = openpyxl.load_workbook(str(file_path), read_only=True)
    ws = wb.active

    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(h).strip() if h else "" for h in next(rows_iter)]

    # 验证是否包含必要的列
    has_tcm_name = "TCM_name" in headers or "TCMBank_ID" in headers
    if not has_tcm_name:
        wb.close()
        raise ValueError(f"无法识别 TCMbank 格式 (列名: {headers})")

    records: list[HerbIngestionRecord] = []
    errors: list[str] = []
    for row in rows_iter:
        row_dict = dict(zip(headers, row))
        try:
            record = parse_tcmbank_herb_row(row_dict, str(file_path))
            if record:
                records.append(record)
        except ValueError as exc:
            errors.append(str(exc))

    wb.close()

    if errors:
        import logging
        logger = logging.getLogger(__name__)
        for err in errors:
            logger.warning("跳过 TCMbank 行: %s", err)

    return records