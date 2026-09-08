from __future__ import annotations

import pytest
from pydantic import ValidationError

from tcm_mcp_server.web.schema.domain import (
    CaseIntake,
    ConsultationResult,
    EvidenceItem,
    RedFlagAssessment,
    SafetyAssessment,
    SyndromeCandidate,
)
from tcm_mcp_server.web.schema.review import (
    CaseSnapshot,
    Claim,
    CoverageItem,
    Recommendation,
    ReviewReport,
)
from tcm_mcp_server.web.service.review_service import (
    ReviewAssemblyError,
    build_report_draft,
)


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


def make_snapshot(case: CaseIntake) -> CaseSnapshot:
    return CaseSnapshot(case_id="case-1", owner_id="owner-1", version=1, intake=case)


def make_consultation(
    case: CaseIntake,
    *,
    evidence: list[EvidenceItem] | None = None,
    candidates: list[SyndromeCandidate] | None = None,
) -> ConsultationResult:
    return ConsultationResult(
        case=case,
        red_flags=RedFlagAssessment(
            status="clear",
            recommended_action="继续补充资料",
        ),
        evidence=evidence or [],
        syndrome_candidates=candidates or [],
        safety=SafetyAssessment(
            status="insufficient",
            reasons=["no prescription candidate was provided"],
            checked_inputs=["red_flags", "allergies", "current_medications"],
        ),
        answer="仅提供资料摘要。",
    )


def test_build_report_draft_rechecks_deterministic_safety() -> None:
    case = make_case()
    report = build_report_draft(
        make_consultation(case, evidence=[make_evidence()]),
        make_snapshot(case),
        run_id="run-1",
    )

    assert report.status == "draft"
    assert report.coverage["evidence"].status == "reviewed"
    assert report.recommendations == []


def test_build_report_rejects_tampered_model_safety() -> None:
    case = make_case()
    consultation = make_consultation(case).model_copy(
        update={"safety": SafetyAssessment(status="passed")}
    )

    with pytest.raises(ReviewAssemblyError, match="safety"):
        build_report_draft(consultation, make_snapshot(case), run_id="run-1")


def test_report_rejects_claims_with_unknown_evidence() -> None:
    with pytest.raises(ValidationError, match="unknown evidence"):
        ReviewReport(
            report_id="report-1",
            version=1,
            case_id="case-1",
            case_version=1,
            run_id="run-1",
            evidence=[],
            claims=[
                Claim(
                    claim_id="claim-1",
                    text="候选分析",
                    claim_type="analysis",
                    evidence_ids=["missing"],
                    verification_reason="待核查",
                )
            ],
            coverage={"evidence": CoverageItem(status="insufficient_data", reason="缺失")},
        )


def test_approved_report_cannot_contain_unverified_claim() -> None:
    case = make_case()
    evidence = make_evidence()
    with pytest.raises(ValidationError, match="approved reports"):
        ReviewReport(
            report_id="report-1",
            version=1,
            case_id="case-1",
            case_version=1,
            run_id="run-1",
            status="approved",
            evidence=[evidence],
            claims=[
                Claim(
                    claim_id="claim-1",
                    text="候选分析",
                    claim_type="analysis",
                    evidence_ids=[evidence.evidence_id],
                    verification_reason="尚未核查",
                )
            ],
            coverage={"evidence": CoverageItem(status="reviewed", reason="已定位")},
        )


def test_published_recommendation_requires_approved_report_and_references() -> None:
    case = make_case()
    evidence = make_evidence()
    with pytest.raises(ValidationError, match="approved report"):
        ReviewReport(
            report_id="report-1",
            version=1,
            case_id="case-1",
            case_version=1,
            run_id="run-1",
            status="ready",
            evidence=[evidence],
            claims=[],
            recommendations=[
                Recommendation(
                    recommendation_id="rec-1",
                    text="需要专业复核",
                    publication_status="published",
                )
            ],
            coverage={"evidence": CoverageItem(status="reviewed", reason="已定位")},
        )
