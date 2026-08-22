from __future__ import annotations

import json
import os
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class McpEvidenceItem(BaseModel):
    """Transport-safe evidence metadata attached to one MCP tool result."""

    model_config = ConfigDict(
        alias_generator=lambda field_name: {
            "evidence_id": "evidenceId",
            "source_hash": "sourceHash",
            "dataset_version": "datasetVersion",
            "retrieval_method": "retrievalMethod",
            "retrieval_score": "retrievalScore",
        }.get(field_name, field_name),
        populate_by_name=True,
        extra="forbid",
    )

    evidence_id: str = Field(..., min_length=1, max_length=128)
    source: str = Field(..., min_length=1, max_length=500)
    title: str = Field(..., min_length=1, max_length=500)
    source_hash: str = Field(..., min_length=64, max_length=64)
    dataset_version: str = Field(..., min_length=1, max_length=128)
    retrieval_method: Literal["exact", "keyword", "vector", "hybrid"]
    retrieval_score: float | None = Field(None, ge=0, le=1)
    excerpt: str = Field(..., min_length=1, max_length=5000)


class McpResponseEnvelope(BaseModel):
    """Versioned JSON response used on the MCP text transport."""

    model_config = ConfigDict(
        alias_generator=lambda field_name: {
            "schema_version": "schemaVersion",
            "tool_name": "toolName",
        }.get(field_name, field_name),
        populate_by_name=True,
        extra="forbid",
    )

    schema_version: Literal[1] = 1
    tool_name: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., max_length=100000)
    evidence: list[McpEvidenceItem] = Field(default_factory=list, max_length=32)


def _retrieval_method(tool_name: str, arguments: dict[str, object]) -> str:
    if tool_name == "tcm_drug_interaction_check":
        return "exact"
    if tool_name in {"tcm_diagnosis_syndrome", "tcm_classic_case_search"}:
        return "vector"
    if arguments.get("name") and not any(
        arguments.get(field) for field in ("nature", "taste", "meridian", "keywords", "symptoms", "herbs")
    ):
        return "exact"
    if arguments:
        return "hybrid"
    return "keyword"


def build_mcp_response(
    tool_name: str,
    arguments: dict[str, object],
    content: str,
    evidence: list[McpEvidenceItem] | None = None,
) -> McpResponseEnvelope:
    """Wrap a legacy Markdown result with deterministic trace metadata.

    The hash intentionally covers the canonical request and returned content. Until
    every tool exposes row-level evidence, this identifies the exact result artifact
    without inventing a database record identifier.
    """

    canonical_payload = json.dumps(
        {"arguments": arguments, "content": content, "toolName": tool_name},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    result_hash = sha256(canonical_payload.encode("utf-8")).hexdigest()
    dataset_version = os.getenv("TCM_AGENT_DATASET_VERSION", "seed-v1")
    fallback_evidence = McpEvidenceItem(
        evidence_id=f"mcp:{tool_name}:{result_hash[:24]}",
        source=f"tcm-mcp-server:{dataset_version}",
        title=f"{tool_name} result",
        source_hash=result_hash,
        dataset_version=dataset_version,
        retrieval_method=_retrieval_method(tool_name, arguments),
        excerpt=content[:5000] or "No result content was returned.",
    )
    return McpResponseEnvelope(
        tool_name=tool_name,
        content=content,
        evidence=evidence or [fallback_evidence],
    )
