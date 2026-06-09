"""Deterministic parser for HERB database xlsx exports."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .schema import (
    HerbIngestionRecord,
    Nature,
    VALID_TASTES,
    TCM_PROPERTY_MAP,
    translate_property,
    translate_meridian,
)


# 可用作 Nature 的中文值
NATURE_CHINESE = frozenset({"寒", "热", "温", "凉", "平", "大寒", "大热", "微寒", "微温"})


def _normalize_value(value: Any) -> str:
    """Convert a cell value to string, treating None/NA as empty."""
    if value is None:
        return ""
    s = str(value).strip()
    if s in ("NA", "NaN", "None", ""):
        return ""
    return s


def parse_herb_xlsx_row(row: dict[str, Any], source_file: str) -> HerbIngestionRecord | None:
    """Parse a single row from HERB-herbs.xlsx into a HerbIngestionRecord.

    Expected columns (case-insensitive):
      - Herb_cn_name  → name
      - Category      → category
      - Properties    → nature (translated from English)
      - Taste         → taste (translated from English)
      - Meridians     → meridian (translated from English)
      - Function      → effect
      - Indication    → indication
      - Toxicity      → toxicity
    """
    name = _normalize_value(row.get("Herb_cn_name") or row.get("Herb_Cn_name", ""))
    if not name:
        return None

    category = _normalize_value(row.get("Category", ""))
    raw_properties = _normalize_value(row.get("Properties", ""))
    raw_taste = _normalize_value(row.get("Taste", ""))
    raw_meridian = _normalize_value(row.get("Meridians", ""))
    effect = _normalize_value(row.get("Function", "")) or "未收录"
    indication = _normalize_value(row.get("Indication", "")) or "未收录"
    toxicity = _normalize_value(row.get("Toxicity", ""))
    aliases = _normalize_value(row.get("Alias", ""))
    source = _normalize_value(row.get("Source", "")) or "HERB"

    # 收集并智能分拣所有属性分词（性、味）
    nature_parts = []
    taste_parts = []

    all_properties = []
    if raw_properties:
        all_properties.extend(translate_property(raw_properties).replace("；", ";").replace(",", ";").replace("，", ";").split(";"))
    if raw_taste:
        all_properties.extend(translate_property(raw_taste).replace("；", ";").replace(",", ";").replace("，", ";").split(";"))

    for part in all_properties:
        part = part.strip()
        if not part:
            continue
        if part in NATURE_CHINESE:
            nature_parts.append(part)
        elif part in VALID_TASTES:
            taste_parts.append(part)
        else:
            # 未识别的属性值默认分到 taste（味道）中，由校验器决定是否拦截
            taste_parts.append(part)

    # 去重并拼接，性取首个，味用顿号
    nature = nature_parts[0] if nature_parts else "平"

    seen_tastes = []
    for t in taste_parts:
        if t not in seen_tastes:
            seen_tastes.append(t)
    taste = "、".join(seen_tastes) if seen_tastes else "甘"

    meridian = translate_meridian(raw_meridian) if raw_meridian else "肝"

    # 构建 source_text
    source_lines = [
        f"名称: {name}",
        f"分类: {category}",
        f"归经: {raw_meridian}",
        f"功效: {effect}",
        f"主治: {indication}",
    ]
    source_text = "\n".join(line for line in source_lines if line)

    payload = {
        "name": name,
        "category": category or "未分类",
        "nature": nature,
        "taste": taste,
        "meridian": meridian,
        "effect": effect,
        "indication": indication,
        "toxicity": toxicity or "无毒",
        "aliases": aliases,
        "source": source,
        "source_file": source_file,
        "source_heading": name,
        "source_text": source_text or name,
        "source_hash": sha256(source_text.encode("utf-8")).hexdigest() if source_text else sha256(name.encode("utf-8")).hexdigest(),
        "parser_version": "herb-xlsx-v1",
    }

    try:
        return HerbIngestionRecord(**payload)
    except ValidationError as exc:
        raise ValueError(f"HERB xlsx 行校验失败 ({name}): {exc}") from exc


def parse_herb_xlsx(path: str | Path) -> list[HerbIngestionRecord]:
    """Parse all rows from a HERB-herbs.xlsx file."""
    import openpyxl  # lazy import

    file_path = Path(path)
    wb = openpyxl.load_workbook(str(file_path), read_only=True)
    ws = wb.active

    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(h).strip() if h else "" for h in next(rows_iter)]

    records: list[HerbIngestionRecord] = []
    errors: list[str] = []
    for row in rows_iter:
        row_dict = dict(zip(headers, row))
        try:
            record = parse_herb_xlsx_row(row_dict, str(file_path))
            if record:
                records.append(record)
        except ValueError as exc:
            errors.append(str(exc))

    wb.close()

    if errors:
        import logging
        logger = logging.getLogger(__name__)
        for err in errors:
            logger.warning("跳过 HERB 行: %s", err)

    return records