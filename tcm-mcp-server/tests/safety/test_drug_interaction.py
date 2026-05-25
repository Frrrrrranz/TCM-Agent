from __future__ import annotations

import json
import asyncio
from pathlib import Path

import pytest


DATASET = Path(__file__).resolve().parents[1] / "datasets" / "drug_interaction.json"


def load_cases() -> list[dict]:
    return json.loads(DATASET.read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", load_cases(), ids=lambda case: case["id"])
def test_drug_interaction_dataset(seeded_db, case: dict) -> None:
    conflicts = seeded_db.check_drug_interaction(case["herbs"])
    conflict_types = {conflict["type"] for conflict in conflicts}

    if case["type"] is None:
        assert not conflict_types
    else:
        assert case["type"] in conflict_types


def test_drug_interaction_pipeline_marks_severe_conflicts(pipeline) -> None:
    output = asyncio.run(pipeline.check_drug_interaction(["附子", "半夏"]))

    assert "[严重] **十八反**" in output
    assert "附子与半夏相反" in output
    assert "安全提示" in output
