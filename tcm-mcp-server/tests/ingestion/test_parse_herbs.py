from __future__ import annotations

import pytest

from tcm_mcp_server.data.parse_herbs import parse_herb_markdown


VALID_HERB = """
## 桂枝

- 类别：解表药
- 异名：
- 性味：辛、甘，温
- 归经：心、肺、膀胱经
- 功效：发汗解肌，温通经脉，助阳化气
- 主治：风寒感冒，脘腹冷痛，血寒经闭，关节痹痛，痰饮，水肿，心悸
- 用量：3-10g
- 用法：煎服
- 禁忌：
- 毒性：无毒
- 来源：《中药学》十三五规划教材
"""


def test_parse_herb_markdown_extracts_structured_fields() -> None:
    record = parse_herb_markdown(VALID_HERB, "raw/herbology/解表药.md")

    assert record.name == "桂枝"
    assert record.category == "解表药"
    assert record.nature == "温"
    assert record.taste == "辛、甘"
    assert record.meridian == "心、肺、膀胱经"
    assert record.source_file == "raw/herbology/解表药.md"
    assert record.source_heading == "桂枝"
    assert len(record.source_hash) == 64


def test_parse_herb_markdown_rejects_invalid_enum_values() -> None:
    bad = VALID_HERB.replace("辛、甘，温", "甜、温")

    with pytest.raises(ValueError, match="invalid taste"):
        parse_herb_markdown(bad)
