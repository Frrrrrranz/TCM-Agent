"""Deterministic parser for TCM Formula xlsx exports.

Supports:
  - ETCM-formulas.xlsx (primary)
  - HERB_formula_info_v2.xlsx
  - TCM formula.xlsx (minimal, pinyin only)
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .schema import PrescriptionIngestionRecord


def _normalize_value(value: Any) -> str:
    """Convert a cell value to string, treating None/NA as empty."""
    if value is None:
        return ""
    s = str(value).strip()
    if s in ("NA", "NaN", "None", ""):
        return ""
    return s


def _normalize_herb_list(value: str) -> str:
    """Normalize a comma/separated herb list into canonical form."""
    if not value:
        return ""
    # 统一分隔符为逗号
    for sep in ("；", ";", "、", "/", "，"):
        value = value.replace(sep, ",")
    herbs = [h.strip() for h in value.split(",") if h.strip()]
    return ", ".join(herbs)


# ── ETCM 解析 ──────────────────────────────────────────

def parse_etcm_row(row: dict[str, Any], source_file: str) -> PrescriptionIngestionRecord | None:
    """Parse one row from ETCM-formulas.xlsx."""
    name = _normalize_value(row.get("Formula Name in Chinese", ""))
    if not name:
        name = _normalize_value(row.get("Formula Name in Pinyin", ""))
    if not name:
        return None

    composition = _normalize_herb_list(
        _normalize_value(row.get("Herbs Contained in This Formula (Chinese)", ""))
        or _normalize_value(row.get("Herbs Contained in This Formula (Chinese Pinyin)", ""))
    )
    indication = _normalize_value(row.get("Indications in Chinese", ""))
    syndrome = _normalize_value(row.get("Syndromes in Chinese", ""))
    category = _normalize_value(row.get("Type", ""))
    dosage_form = _normalize_value(row.get("Dosage Form", ""))

    source_text_lines = [
        f"名称: {name}",
        f"组成: {composition}",
        f"主治: {indication}",
        f"证型: {syndrome}",
    ]
    source_text = "\n".join(l for l in source_text_lines if l)

    payload = {
        "name": name,
        "source": "ETCM",
        "category": category,
        "composition": composition,
        "indication": indication,
        "syndrome": syndrome,
        "usage": dosage_form,
        "source_file": source_file,
        "source_heading": name,
        "source_text": source_text or name,
        "source_hash": sha256(source_text.encode("utf-8")).hexdigest() if source_text else sha256(name.encode("utf-8")).hexdigest(),
        "parser_version": "formula-etcm-v1",
    }

    try:
        return PrescriptionIngestionRecord(**payload)
    except ValidationError as exc:
        raise ValueError(f"ETCM 行校验失败 ({name}): {exc}") from exc


# ── HERB 方剂解析 ──────────────────────────────────────

HERB_COLUMN_MAP = {
    "Formula_cn_name": "name",
    "Herbs_in_Chinese": "composition",
    "Syndromes_in_Chinese": "syndrome",
    "Indications_in_Chinese": "indication",
    "Category": "category",
    "Dosage_form": "usage",
    "Administration": "administration",
    "Source": "source",
}


def parse_herb_formula_row(row: dict[str, Any], source_file: str) -> PrescriptionIngestionRecord | None:
    """Parse one row from HERB_formula_info_v2.xlsx."""
    name = _normalize_value(row.get("Formula_cn_name", ""))
    if not name:
        name = _normalize_value(row.get("Formula_pinyin_name", ""))
    if not name:
        return None

    composition = _normalize_herb_list(_normalize_value(row.get("Herbs_in_Chinese", "")))
    syndrome = _normalize_value(row.get("Syndromes_in_Chinese", ""))
    indication = _normalize_value(row.get("Indications_in_Chinese", ""))
    category = _normalize_value(row.get("Category", ""))
    dosage_form = _normalize_value(row.get("Dosage_form", ""))
    source = _normalize_value(row.get("Source", "")) or "HERB"

    source_text_lines = [
        f"名称: {name}",
        f"组成: {composition}",
        f"主治: {indication}",
        f"证型: {syndrome}",
    ]
    source_text = "\n".join(l for l in source_text_lines if l)

    payload = {
        "name": name,
        "source": source,
        "category": category,
        "composition": composition,
        "indication": indication,
        "syndrome": syndrome,
        "usage": dosage_form,
        "source_file": source_file,
        "source_heading": name,
        "source_text": source_text or name,
        "source_hash": sha256(source_text.encode("utf-8")).hexdigest() if source_text else sha256(name.encode("utf-8")).hexdigest(),
        "parser_version": "formula-herb-v1",
    }

    try:
        return PrescriptionIngestionRecord(**payload)
    except ValidationError as exc:
        raise ValueError(f"HERB formula 行校验失败 ({name}): {exc}") from exc


# ── TCM Formula 精简版解析 ─────────────────────────────

def parse_tcm_formula_row(row: dict[str, Any], source_file: str) -> PrescriptionIngestionRecord | None:
    """Parse one row from TCM formula.xlsx (minimal)."""
    name = _normalize_value(row.get("Formula Name in Chinese", ""))
    if not name:
        name = _normalize_value(row.get("Formula Name in Pinyin", ""))
    if not name:
        return None

    composition_pinyin = _normalize_herb_list(
        _normalize_value(row.get("Herbs Contained in This Formula (Chinese Pinyin)", ""))
    )
    # 将拼音组成转为中文（通过 parse_herbs.reverse_pinyin_map 在批量脚本中处理）
    # 这里先保存拼音形式，后续合并时做拼音→中文映射
    composition = composition_pinyin

    source_text = f"名称: {name}\n组成: {composition}"

    payload = {
        "name": name,
        "source": "TCM formula.xlsx",
        "composition": composition,
        "source_file": source_file,
        "source_heading": name,
        "source_text": source_text,
        "source_hash": sha256(source_text.encode("utf-8")).hexdigest(),
        "parser_version": "formula-tcm-xlsx-v1",
    }

    try:
        return PrescriptionIngestionRecord(**payload)
    except ValidationError as exc:
        raise ValueError(f"TCM formula 行校验失败 ({name}): {exc}") from exc


# ── 通用入口 ───────────────────────────────────────────

PARSER_DISPATCH = {
    "etcm": ("Formula Name in Chinese", parse_etcm_row),
    "herb_formula": ("Formula_cn_name", parse_herb_formula_row),
    "tcm_formula": ("Formula Name in Chinese", parse_tcm_formula_row),
}


def detect_parser(headers: list[str]) -> str | None:
    """Auto-detect which parser to use based on column headers."""
    header_set = {h.strip() for h in headers}
    if "Formula_cn_name" in header_set:
        return "herb_formula"
    if "Formula Name in Chinese" in header_set:
        if "Herbs Contained in This Formula (Chinese Pinyin)" in header_set and \
           "Herbs Contained in This Formula (Chinese)" not in header_set:
            return "tcm_formula"
        return "etcm"
    return None


def parse_formula_xlsx(path: str | Path) -> list[PrescriptionIngestionRecord]:
    """Parse all rows from a formula xlsx file (auto-detects format)."""
    import openpyxl  # lazy import

    file_path = Path(path)
    wb = openpyxl.load_workbook(str(file_path), read_only=True)
    ws = wb.active

    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(h).strip() if h else "" for h in next(rows_iter)]

    parser_key = detect_parser(headers)
    if not parser_key:
        wb.close()
        raise ValueError(f"无法识别方剂 xlsx 格式 (列名: {headers})")

    _, parse_row = PARSER_DISPATCH[parser_key]

    records: list[PrescriptionIngestionRecord] = []
    errors: list[str] = []
    for row in rows_iter:
        row_dict = dict(zip(headers, row))
        try:
            record = parse_row(row_dict, str(file_path))
            if record:
                records.append(record)
        except ValueError as exc:
            errors.append(str(exc))

    wb.close()

    if errors:
        import logging
        logger = logging.getLogger(__name__)
        for err in errors:
            logger.warning("跳过 formula 行: %s", err)

    return records