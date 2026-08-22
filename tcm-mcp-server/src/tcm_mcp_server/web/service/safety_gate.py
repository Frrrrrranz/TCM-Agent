from __future__ import annotations

from collections.abc import Iterable

from ..schema.domain import (
    CaseIntake,
    PrescriptionCandidate,
    RedFlagAssessment,
    SafetyAssessment,
)


def assess_prescription_safety(
    case: CaseIntake,
    red_flags: RedFlagAssessment,
    candidates: Iterable[PrescriptionCandidate],
    interaction_conflicts: Iterable[dict[str, object]] = (),
) -> SafetyAssessment:
    """Return a fail-closed assessment for reference-only formula candidates."""

    candidate_list = list(candidates)
    reasons: list[str] = []
    checked_inputs = ["red_flags", "allergies", "current_medications"]

    if not candidate_list:
        return SafetyAssessment(
            status="insufficient",
            reasons=["no prescription candidate was provided"],
            checked_inputs=checked_inputs,
        )
    if red_flags.status != "clear":
        reasons.append("red flags are unresolved")
    if case.pregnancy_status == "unknown":
        reasons.append("pregnancy status is unknown")
    if not case.allergies:
        reasons.append("allergy history is incomplete")
    if any(conflict.get("severity") == "error" for conflict in interaction_conflicts):
        reasons.append("severe herb interaction conflict was detected")

    if reasons:
        return SafetyAssessment(
            status="blocked",
            reasons=reasons,
            checked_inputs=checked_inputs,
        )
    return SafetyAssessment(
        status="passed",
        reasons=[],
        checked_inputs=checked_inputs,
    )
