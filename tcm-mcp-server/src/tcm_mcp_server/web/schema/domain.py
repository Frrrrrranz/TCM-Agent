from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CaseIntake(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chief_complaint: str = Field(..., min_length=1, max_length=2000)
    symptoms: list[str] = Field(..., min_length=1, max_length=32)
    tongue: str | None = Field(None, max_length=500)
    pulse: str | None = Field(None, max_length=500)
    age: int | None = Field(None, ge=0, le=130)
    sex: Literal["unknown", "female", "male", "other"] = "unknown"
    pregnancy_status: Literal[
        "unknown", "not_pregnant", "pregnant", "postpartum"
    ] = "unknown"
    allergies: list[str] = Field(default_factory=list, max_length=32)
    current_medications: list[str] = Field(default_factory=list, max_length=64)
    relevant_history: list[str] = Field(default_factory=list, max_length=64)


class RedFlagAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["clear", "needs_escalation", "insufficient"]
    reasons: list[str] = Field(default_factory=list, max_length=32)
    recommended_action: str = Field(..., min_length=1, max_length=1000)

    @model_validator(mode="after")
    def require_reason_for_non_clear(self) -> "RedFlagAssessment":
        if self.status != "clear" and not self.reasons:
            raise ValueError("non-clear red-flag assessments require reasons")
        return self


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(..., min_length=1, max_length=128)
    source: str = Field(..., min_length=1, max_length=500)
    title: str = Field(..., min_length=1, max_length=500)
    source_hash: str = Field(..., min_length=1, max_length=128)
    dataset_version: str = Field(..., min_length=1, max_length=128)
    retrieval_method: Literal["exact", "keyword", "vector", "hybrid"]
    retrieval_score: float | None = Field(None, ge=0, le=1)
    excerpt: str = Field(..., min_length=1, max_length=5000)


class SyndromeCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=300)
    confidence: float | None = Field(None, ge=0, le=1)
    supporting_evidence_ids: list[str] = Field(..., min_length=1, max_length=32)
    missing_information: list[str] = Field(default_factory=list, max_length=32)
    contradictory_evidence_ids: list[str] = Field(default_factory=list, max_length=32)


class PrescriptionCandidate(BaseModel):
    """Reference-only formula candidate; dosage is intentionally not a field."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=300)
    reference_only: Literal[True] = True
    supporting_evidence_ids: list[str] = Field(..., min_length=1, max_length=32)
    indications: list[str] = Field(default_factory=list, max_length=32)
    contraindications: list[str] = Field(default_factory=list, max_length=32)


class SafetyAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["passed", "blocked", "insufficient"]
    reasons: list[str] = Field(default_factory=list, max_length=32)
    checked_inputs: list[str] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def require_reason_for_failure(self) -> "SafetyAssessment":
        if self.status != "passed" and not self.reasons:
            raise ValueError("blocked or insufficient safety requires reasons")
        return self


class ConsultationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case: CaseIntake
    red_flags: RedFlagAssessment
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=128)
    syndrome_candidates: list[SyndromeCandidate] = Field(default_factory=list, max_length=16)
    prescription_candidates: list[PrescriptionCandidate] = Field(
        default_factory=list, max_length=16
    )
    safety: SafetyAssessment
    answer: str = Field(..., min_length=1, max_length=12000)
    disclaimer: str = Field(
        default="仅供学习与资料检索参考，不能替代面诊、诊断或处方。",
        min_length=1,
        max_length=500,
    )

    @model_validator(mode="after")
    def enforce_fail_closed_output(self) -> "ConsultationResult":
        if self.prescription_candidates and self.safety.status != "passed":
            raise ValueError(
                "prescription candidates cannot be published before safety passes"
            )
        if self.prescription_candidates and self.red_flags.status != "clear":
            raise ValueError(
                "prescription candidates cannot be published with unresolved red flags"
            )
        return self
