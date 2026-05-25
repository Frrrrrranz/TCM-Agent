"""Deterministic parser for normalized herb Markdown."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re

from pydantic import ValidationError

from .normalize_markdown import normalize_text
from .schema import HerbIngestionRecord


FIELD_MAP = {
    "类别": "category",
    "异名": "aliases",
    "性味": "nature_taste",
    "归经": "meridian",
    "功效": "effect",
    "主治": "indication",
    "用量": "usage",
    "用法": "method",
    "禁忌": "caution",
    "毒性": "toxicity",
    "来源": "source",
}


def split_nature_taste(value: str) -> tuple[str, str]:
    """Split a common 性味 field such as 辛、甘、温 into nature and taste."""
    parts = [part.strip() for part in re.split(r"[、,，]", value) if part.strip()]
    natures = {"寒", "热", "温", "凉", "平", "大寒", "大热", "微寒", "微温"}
    nature = next((part for part in reversed(parts) if part in natures), "")
    tastes = [part for part in parts if part != nature]
    return nature, "、".join(tastes)


def parse_herb_markdown(text: str, source_file: str = "<memory>") -> HerbIngestionRecord:
    """Parse a single normalized herb Markdown entry."""
    normalized = normalize_text(text)
    lines = [line for line in normalized.splitlines() if line.strip()]
    title_line = next((line for line in lines if line.startswith("## ")), "")
    if not title_line:
        raise ValueError("missing herb heading")

    name = title_line.removeprefix("## ").strip()
    fields: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^-\s*([^:]+):\s*(.*)$", line)
        if not match:
            continue
        raw_field = match.group(1).strip()
        key = FIELD_MAP.get(raw_field)
        if key:
            fields[key] = match.group(2).strip()

    nature, taste = split_nature_taste(fields.pop("nature_taste", ""))
    source_text = normalized.strip()
    payload = {
        "name": name,
        "nature": nature,
        "taste": taste,
        "source_file": source_file,
        "source_heading": name,
        "source_text": source_text,
        "source_hash": sha256(source_text.encode("utf-8")).hexdigest(),
        **fields,
    }

    try:
        return HerbIngestionRecord(**payload)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


def parse_herb_file(path: str | Path) -> HerbIngestionRecord:
    file_path = Path(path)
    return parse_herb_markdown(file_path.read_text(encoding="utf-8"), str(file_path))
