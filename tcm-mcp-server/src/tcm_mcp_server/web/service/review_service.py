from __future__ import annotations

from uuid import uuid4

from ..schema.domain import ConsultationResult
from ..schema.review import (
    CaseSnapshot,
    Claim,
    CoverageItem,
    Finding,
    Recommendation,
    ReviewReport,
)
from .safety_gate import assess_prescription_safety


class ReviewAssemblyError(ValueError):
    """Raised when a consultation cannot become a traceable report draft."""


def build_report_draft(
    consultation: ConsultationResult,
    case: CaseSnapshot,
    run_id: str,
    report_id: str | None = None,
) -> ReviewReport:
    """Convert a validated consultation into a non-publishable report draft.

    The safety rule is deliberately re-evaluated at this boundary. A model-provided
    safety field is data, not an authorization to publish a recommendation.
    """

    expected_safety = assess_prescription_safety(
        consultation.case,
        consultation.red_flags,
        consultation.prescription_candidates,
    )
    if expected_safety != consultation.safety:
        raise ReviewAssemblyError("consultation safety does not match deterministic rule output")
    if consultation.case != case.intake:
        raise ReviewAssemblyError("consultation case does not match the requested snapshot")

    claims = [
        Claim(
            claim_id=f"claim-{uuid4().hex[:12]}",
            text=f"候选证型：{candidate.name}",
            claim_type="analysis",
            evidence_ids=candidate.supporting_evidence_ids,
            contradictory_evidence_ids=candidate.contradictory_evidence_ids,
            verification_status="unverified",
            verification_reason="候选分析尚未经过独立证据核查",
        )
        for candidate in consultation.syndrome_candidates
    ]

    findings: list[Finding] = []
    if consultation.red_flags.status != "clear":
        findings.append(
            Finding(
                finding_id=f"finding-{uuid4().hex[:12]}",
                category="red_flag",
                severity="critical" if consultation.red_flags.status == "needs_escalation" else "warning",
                text=consultation.red_flags.recommended_action,
                status="open",
            )
        )
    if consultation.safety.status != "passed":
        findings.append(
            Finding(
                finding_id=f"finding-{uuid4().hex[:12]}",
                category="risk",
                severity="warning",
                text="；".join(consultation.safety.reasons),
                status="insufficient" if consultation.safety.status == "insufficient" else "open",
            )
        )

    if not consultation.evidence:
        evidence_coverage = CoverageItem(
            status="insufficient_data", reason="当前结果没有可定位的证据项"
        )
    else:
        evidence_coverage = CoverageItem(status="reviewed", reason="证据项已保留来源和版本定位")

    has_missing_information = any(
        candidate.missing_information for candidate in consultation.syndrome_candidates
    )
    coverage = {
        "case_data": CoverageItem(
            status="insufficient_data" if has_missing_information else "reviewed",
            reason="候选分析仍有待补充字段" if has_missing_information else "已接收病例输入",
        ),
        "evidence": evidence_coverage,
        "medication_risk": CoverageItem(
            status="unsupported" if not consultation.prescription_candidates else "reviewed",
            reason=(
                "本次没有方剂候选，不对用药风险作结论"
                if not consultation.prescription_candidates
                else "已执行当前安全规则，仍需专业复核"
            ),
        ),
    }
    return ReviewReport(
        report_id=report_id or f"report-{uuid4().hex[:12]}",
        version=1,
        case_id=case.case_id,
        case_version=case.version,
        run_id=run_id,
        status="incomplete" if not consultation.evidence else "draft",
        evidence=consultation.evidence,
        claims=claims,
        findings=findings,
        recommendations=[],
        coverage=coverage,
    )
