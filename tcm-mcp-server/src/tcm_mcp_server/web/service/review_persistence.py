from __future__ import annotations

from ..repository.review import ReviewRepository
from ..schema.domain import ConsultationResult
from ..schema.review import CaseSnapshot, ReviewReport
from .review_service import build_report_draft


def create_and_persist_report_draft(
    consultation: ConsultationResult,
    case: CaseSnapshot,
    run_id: str,
    report_id: str | None = None,
) -> ReviewReport:
    """Build a fail-closed draft and persist its immutable input/output versions."""

    report = build_report_draft(
        consultation=consultation,
        case=case,
        run_id=run_id,
        report_id=report_id,
    )
    ReviewRepository.save_case_snapshot(case)
    ReviewRepository.save_report(report, owner_id=case.owner_id)
    return report
