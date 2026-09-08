from __future__ import annotations

from pathlib import Path

import pytest

from tcm_mcp_server.web.memory import db
from tcm_mcp_server.web.repository.review import ReviewRepository, ReviewStoreError
from tcm_mcp_server.web.schema.domain import (
    CaseIntake,
    ConsultationResult,
    RedFlagAssessment,
    SafetyAssessment,
)
from tcm_mcp_server.web.schema.review import CaseSnapshot
from tcm_mcp_server.web.service.review_persistence import (
    create_and_persist_report_draft,
)
from tcm_mcp_server.web.service.review_service import build_report_draft


def make_case() -> CaseIntake:
    return CaseIntake(
        chief_complaint="学习性资料检索案例",
        symptoms=["头痛"],
        age=30,
        sex="female",
        pregnancy_status="not_pregnant",
        allergies=["无已知药物过敏"],
        current_medications=["无"],
    )


def make_snapshot(owner_id: str = "owner-1", version: int = 1) -> CaseSnapshot:
    return CaseSnapshot(
        case_id="case-1",
        owner_id=owner_id,
        version=version,
        intake=make_case(),
    )


def make_consultation() -> ConsultationResult:
    return ConsultationResult(
        case=make_case(),
        red_flags=RedFlagAssessment(
            status="clear",
            recommended_action="继续补充资料",
        ),
        safety=SafetyAssessment(
            status="insufficient",
            reasons=["no prescription candidate was provided"],
            checked_inputs=["red_flags", "allergies", "current_medications"],
        ),
        answer="仅提供资料摘要。",
    )


@pytest.fixture
def isolated_review_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "review.db"
    monkeypatch.setattr(db, "DB_PATH", path)
    return path


def test_report_draft_persists_case_and_report_versions(isolated_review_db: Path) -> None:
    snapshot = make_snapshot()
    report = create_and_persist_report_draft(make_consultation(), snapshot, "run-1")

    assert ReviewRepository.get_case_snapshot("case-1", 1, "owner-1") == snapshot
    assert ReviewRepository.get_report(report.report_id, 1, "owner-1") == report


def test_case_versions_are_immutable(isolated_review_db: Path) -> None:
    snapshot = make_snapshot()
    ReviewRepository.save_case_snapshot(snapshot)

    with pytest.raises(ReviewStoreError, match="already_exists"):
        ReviewRepository.save_case_snapshot(snapshot)


def test_report_cannot_be_saved_for_another_owner(isolated_review_db: Path) -> None:
    snapshot = make_snapshot(owner_id="owner-1")
    ReviewRepository.save_case_snapshot(snapshot)
    report = create_and_persist_report_draft.__wrapped__(  # type: ignore[attr-defined]
        make_consultation(), snapshot, "run-1"
    ) if hasattr(create_and_persist_report_draft, "__wrapped__") else None
    if report is None:
        from tcm_mcp_server.web.service.review_service import build_report_draft

        report = build_report_draft(make_consultation(), snapshot, "run-1")

    with pytest.raises(ReviewStoreError, match="not_owned"):
        ReviewRepository.save_report(report, owner_id="owner-2")
