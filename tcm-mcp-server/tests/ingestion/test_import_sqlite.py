from __future__ import annotations

from tcm_mcp_server.data.database import Database
from tcm_mcp_server.data.import_sqlite import import_herb_file


VALID_HERB = """
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


REVIEW_HERB = """
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


def test_import_herb_file_writes_clean_record(tmp_path) -> None:
    db = Database(tmp_path / "tcm.db")
    db.connect()
    herb_file = tmp_path / "桂枝.md"
    herb_file.write_text(VALID_HERB, encoding="utf-8")

    imported = import_herb_file(db, herb_file, tmp_path / "review")
    herb = db.get_herb_by_name("桂枝")

    assert imported
    assert herb is not None
    assert herb.source_heading == "桂枝"
    assert len(herb.source_hash) == 64


def test_import_herb_file_sends_unsafe_record_to_review(tmp_path) -> None:
    db = Database(tmp_path / "tcm.db")
    db.connect()
    herb_file = tmp_path / "半夏.md"
    herb_file.write_text(REVIEW_HERB, encoding="utf-8")

    imported = import_herb_file(db, herb_file, tmp_path / "review")

    assert not imported
    assert db.get_herb_by_name("半夏") is None
    assert list((tmp_path / "review").glob("*.json"))
