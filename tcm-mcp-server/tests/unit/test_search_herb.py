from __future__ import annotations

import json
import asyncio
from pathlib import Path

import pytest


DATASET = Path(__file__).resolve().parents[1] / "datasets" / "herb_query.json"


def load_cases() -> list[dict]:
    return json.loads(DATASET.read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", load_cases(), ids=lambda case: case["id"])
def test_search_herb_dataset(seeded_db, case: dict) -> None:
    herb = seeded_db.get_herb_by_name(case["input"]["name"])
    assert herb is not None

    expected = case["expected"]
    for field in ("nature", "taste", "meridian", "toxicity"):
        if field in expected:
            assert getattr(herb, field) == expected[field]

    for value in expected.get("effect_contains", []):
        assert value in herb.effect
    for value in expected.get("indication_contains", []):
        assert value in herb.indication
    for value in expected.get("caution_contains", []):
        assert value in herb.caution


def test_search_herb_pipeline_formats_traceable_result(pipeline) -> None:
    output = asyncio.run(pipeline.search_herb(name="桂枝"))

    assert "## 中药查询结果" in output
    assert "### 桂枝" in output
    assert "发汗解肌" in output
    assert "温热病、阴虚阳盛者忌用" in output
