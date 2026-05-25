from __future__ import annotations

from tcm_mcp_server.data.normalize_markdown import normalize_text


def test_normalize_markdown_field_aliases_and_punctuation() -> None:
    raw = """
## 桂枝

* 分类：解表药
* 性味：辛，甘，温
* 归经：心，肺，膀胱经
* 使用注意：温病表热者慎用
"""

    normalized = normalize_text(raw)

    assert "- 类别: 解表药" in normalized
    assert "- 性味: 辛、甘、温" in normalized
    assert "- 归经: 心、肺、膀胱经" in normalized
    assert "- 禁忌: 温病表热者慎用" in normalized
