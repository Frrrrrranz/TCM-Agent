from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .domain import CaseIntake, EvidenceItem

CoverageStatus = Literal[
    "reviewed",
    "insufficient_data",
    "unsupported",
    "not_applicable",
]
ClaimVerificationStatus = Literal[
    "unverified",
    "supported",
    "unsupported",
    "insufficient",
    "contradicted",
]
ReportStatus = Literal[
    "draft",
    "validating",
    "ready",
    "needs_review",
    "incomplete",
    "approved",
    "superseded",
]


class CaseSnapshot(BaseModel):
    """Immutable case input used by a review run."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., min_length=1, max_length=128)
    owner_id: str = Field(..., min_length=1, max_length=128)
    version: int = Field(..., ge=1)
    intake: CaseIntake
    source_refs: list[str] = Field(default_factory=list, max_length=64)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1, max_length=128)
    case: CaseSnapshot
    target: Literal["case_review", "medication_review", "report_update"]
    scope: list[str] = Field(default_factory=list, max_length=32)
    run_id: str = Field(..., min_length=1, max_length=128)


class CoverageItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: CoverageStatus
    reason: str = Field(..., min_length=1, max_length=500)


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(..., min_length=1, max_length=128)
    text: str = Field(..., min_length=1, max_length=2000)
    claim_type: Literal["fact", "analysis", "risk", "summary"]
    fact_ids: list[str] = Field(default_factory=list, max_length=64)
    evidence_ids: list[str] = Field(default_factory=list, max_length=64)
    contradictory_evidence_ids: list[str] = Field(default_factory=list, max_length=64)
    verification_status: ClaimVerificationStatus = "unverified"
    verification_reason: str = Field(..., min_length=1, max_length=500)


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str = Field(..., min_length=1, max_length=128)
    category: Literal["missing_data", "conflict", "risk", "red_flag"]
    severity: Literal["info", "warning", "critical"]
    text: str = Field(..., min_length=1, max_length=2000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=64)
    status: Literal["open", "confirmed", "insufficient"] = "open"


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation_id: str = Field(..., min_length=1, max_length=128)
    text: str = Field(..., min_length=1, max_length=2000)
    claim_ids: list[str] = Field(default_factory=list, max_length=64)
    evidence_ids: list[str] = Field(default_factory=list, max_length=64)
    requires_professional_review: bool = True
    publication_status: Literal["candidate", "blocked", "published"] = "candidate"


class ReviewReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(..., min_length=1, max_length=128)
    version: int = Field(..., ge=1)
    case_id: str = Field(..., min_length=1, max_length=128)
    case_version: int = Field(..., ge=1)
    run_id: str = Field(..., min_length=1, max_length=128)
    status: ReportStatus = "draft"
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=128)
    claims: list[Claim] = Field(default_factory=list, max_length=128)
    findings: list[Finding] = Field(default_factory=list, max_length=128)
    recommendations: list[Recommendation] = Field(default_factory=list, max_length=64)
    coverage: dict[str, CoverageItem]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_references_and_publication(self) -> "ReviewReport":
        evidence_ids = {item.evidence_id for item in self.evidence}
        claim_ids = {claim.claim_id for claim in self.claims}
        if len(evidence_ids) != len(self.evidence):
            raise ValueError("report evidence_id values must be unique")
        if len(claim_ids) != len(self.claims):
            raise ValueError("report claim_id values must be unique")

        for claim in self.claims:
            references = set(claim.evidence_ids) | set(claim.contradictory_evidence_ids)
            if not references <= evidence_ids:
                raise ValueError(f"claim {claim.claim_id} references unknown evidence")

        for finding in self.findings:
            if not set(finding.evidence_ids) <= evidence_ids:
                raise ValueError(f"finding {finding.finding_id} references unknown evidence")

        for recommendation in self.recommendations:
            if not set(recommendation.claim_ids) <= claim_ids:
                raise ValueError(
                    f"recommendation {recommendation.recommendation_id} references unknown claim"
                )
            if not set(recommendation.evidence_ids) <= evidence_ids:
                raise ValueError(
                    f"recommendation {recommendation.recommendation_id} references unknown evidence"
                )
            if recommendation.publication_status == "published":
                if self.status != "approved":
                    raise ValueError("published recommendations require an approved report")
                if not recommendation.claim_ids or not recommendation.evidence_ids:
                    raise ValueError(
                        "published recommendations require claim and evidence references"
                    )

        if self.status == "approved" and any(
            claim.verification_status != "supported" for claim in self.claims
        ):
            raise ValueError("approved reports cannot contain unverified claims")
        return self


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(..., min_length=1, max_length=128)
    report_version: int = Field(..., ge=1)
    content_hash: str = Field(..., min_length=1, max_length=128)
    decision: Literal["approved", "rejected", "modified"]
    reviewer_id: str = Field(..., min_length=1, max_length=128)
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
