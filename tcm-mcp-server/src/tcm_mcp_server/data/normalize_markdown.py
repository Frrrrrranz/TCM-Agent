"""Markdown normalization for deterministic TCM ingestion."""

from __future__ import annotations

import re


FIELD_ALIASES = {
    "类别": "类别",
    "分类": "类别",
    "异名": "异名",
    "别名": "异名",
    "性味": "性味",
    "归经": "归经",
    "功效": "功效",
    "主治": "主治",
    "用量": "用量",
    "用法": "用法",
    "禁忌": "禁忌",
    "使用注意": "禁忌",
    "毒性": "毒性",
    "来源": "来源",
}


def normalize_text(text: str) -> str:
    """Normalize punctuation, dose separators, and field labels."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("：", ":").replace("，", "、")
    normalized = normalized.replace("－", "-").replace("—", "-")
    normalized = re.sub(r"[ \t]+$", "", normalized, flags=re.MULTILINE)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)

    lines: list[str] = []
    for line in normalized.split("\n"):
        stripped = line.strip()
        match = re.match(r"^[-*]\s*([^:]+):(.*)$", stripped)
        if match:
            field = match.group(1).strip()
            value = match.group(2).strip()
            canonical = FIELD_ALIASES.get(field, field)
            lines.append(f"- {canonical}: {value}")
        elif stripped.startswith("##"):
            title = stripped.lstrip("#").strip()
            lines.append(f"## {title}")
        else:
            lines.append(stripped)

    return "\n".join(lines).strip() + "\n"
