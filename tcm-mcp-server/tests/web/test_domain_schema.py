from __future__ import annotations

import pytest
from pydantic import ValidationError

from tcm_mcp_server.web.schema.domain import (
    CaseIntake,
    ConsultationResult,
    EvidenceItem,
    PrescriptionCandidate,
    RedFlagAssessment,
    SafetyAssessment,
)
from tcm_mcp_server.web.service.safety_gate import assess_prescription_safety


def make_case(**overrides: object) -> CaseIntake:
    values: dict[str, object] = {
        "chief_complaint": "学习性资料检索案例",
        "symptoms": ["头痛"],
        "age": 30,
        "sex": "female",
        "pregnancy_status": "not_pregnant",
        "allergies": ["无已知药物过敏"],
        "current_medications": ["无"],
    }
    values.update(overrides)
    return CaseIntake.model_validate(values)


def make_evidence() -> EvidenceItem:
    return EvidenceItem(
        evidence_id="ev-1",
        source="local-tcm-db",
        title="示例资料",
        source_hash="hash-1",
        dataset_version="test-v1",
        retrieval_method="exact",
        retrieval_score=1.0,
        excerpt="结构化证据摘录",
    )


def make_candidate() -> PrescriptionCandidate:
    return PrescriptionCandidate(
        name="示例方剂",
        supporting_evidence_ids=["ev-1"],
    )


def test_prescription_schema_rejects_dosage_field() -> None:
    with pytest.raises(ValidationError):
        PrescriptionCandidate.model_validate(
            {
                "name": "示例方剂",
                "supporting_evidence_ids": ["ev-1"],
                "dosage": "每日一剂",
            }
        )


def test_safety_gate_blocks_unknown_pregnancy_and_incomplete_allergy_history() -> None:
    case = make_case(pregnancy_status="unknown", allergies=[])
    red_flags = RedFlagAssessment(
        status="clear",
        recommended_action="继续补充资料",
    )
    result = assess_prescription_safety(case, red_flags, [make_candidate()])
    assert result.status == "blocked"
    assert "pregnancy status is unknown" in result.reasons


def test_consultation_result_rejects_prescription_before_safety_pass() -> None:
    with pytest.raises(ValidationError):
        ConsultationResult(
            case=make_case(),
            red_flags=RedFlagAssessment(
                status="needs_escalation",
                reasons=["胸痛"],
                recommended_action="及时就医",
            ),
            evidence=[make_evidence()],
            safety=SafetyAssessment(
                status="blocked",
                reasons=["红旗未排除"],
            ),
            prescription_candidates=[make_candidate()],
            answer="不能提供方剂参考。",
        )
