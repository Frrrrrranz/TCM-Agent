from __future__ import annotations

import json

from tcm_mcp_server.data.parse_herbs import parse_herb_markdown
from tcm_mcp_server.data.review_queue import enqueue_review
from tcm_mcp_server.data.validate_records import validate_herb_record


def test_review_queue_writes_failed_record(tmp_path) -> None:
    raw = """
## 半夏

- 类别：化痰止咳平喘药
- 性味：辛，温
- 归经：脾、胃、肺经
- 功效：燥湿化痰，降逆止呕
- 主治：湿痰寒痰，咳喘痰多
- 用量：3-9g
- 禁忌：反乌头
- 毒性：有毒
- 来源：《中药学》十三五规划教材
"""
    result = validate_herb_record(parse_herb_markdown(raw))

    path = enqueue_review(result, tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["name"] == "半夏"
    assert payload["review_status"] == "needs_review"
    assert payload["review_reasons"]
    assert payload["record"]["source_heading"] == "半夏"
