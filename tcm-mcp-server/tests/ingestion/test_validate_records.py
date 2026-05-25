from __future__ import annotations

from tcm_mcp_server.data.parse_herbs import parse_herb_markdown
from tcm_mcp_server.data.validate_records import validate_herb_record


BASE_HERB = """
## 桂枝

- 类别：解表药
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


def test_validate_herb_record_approves_clean_record() -> None:
    record = parse_herb_markdown(BASE_HERB)
    result = validate_herb_record(record)

    assert result.approved
    assert result.reasons == []


def test_validate_herb_record_requires_review_for_toxicity_and_contraindication() -> None:
    raw = BASE_HERB.replace("## 桂枝", "## 附子")
    raw = raw.replace("毒性：无毒", "毒性：有毒")
    raw = raw.replace("禁忌：", "禁忌：孕妇忌用，反半夏")
    record = parse_herb_markdown(raw)
    result = validate_herb_record(record)

    assert not result.approved
    assert any("毒性药物" in reason for reason in result.reasons)
    assert any("禁忌" in reason for reason in result.reasons)


def test_validate_herb_record_requires_review_for_bad_dose_unit() -> None:
    record = parse_herb_markdown(BASE_HERB.replace("3-10g", "三至十钱"))
    result = validate_herb_record(record)

    assert not result.approved
    assert any("剂量缺少标准单位" in reason for reason in result.reasons)
