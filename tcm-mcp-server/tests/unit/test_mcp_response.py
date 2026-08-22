from __future__ import annotations

import json

from tcm_mcp_server.mcp_response import build_mcp_response


def test_mcp_response_contains_stable_evidence_metadata() -> None:
    arguments = {"name": "妗傛灊"}
    first = build_mcp_response("tcm_search_herb", arguments, "## result")
    second = build_mcp_response("tcm_search_herb", arguments, "## result")

    assert first.evidence[0].evidence_id == second.evidence[0].evidence_id
    assert first.evidence[0].retrieval_method == "exact"
    payload = json.loads(first.model_dump_json(by_alias=True))
    assert payload["schemaVersion"] == 1
    assert payload["toolName"] == "tcm_search_herb"
    assert payload["content"] == "## result"
    assert payload["evidence"][0]["evidenceId"].startswith("mcp:tcm_search_herb:")


def test_mcp_response_changes_when_result_changes() -> None:
    arguments = {"keywords": "清热"}
    first = build_mcp_response("tcm_search_herb", arguments, "first")
    second = build_mcp_response("tcm_search_herb", arguments, "second")

    assert first.evidence[0].evidence_id != second.evidence[0].evidence_id
    assert first.evidence[0].retrieval_method == "hybrid"
