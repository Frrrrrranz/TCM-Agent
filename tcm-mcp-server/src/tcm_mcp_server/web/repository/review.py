from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from ..memory.db import get_connection
from ..schema.review import CaseSnapshot, ReviewReport


class ReviewStoreError(RuntimeError):
    """Raised when a versioned case/report cannot be persisted safely."""


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _content_hash(report: ReviewReport) -> str:
    payload = _canonical_json(report.model_dump(mode="json"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS case_snapshot (
            case_id TEXT NOT NULL,
            owner_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            snapshot_json TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            PRIMARY KEY (case_id, version)
        );
        CREATE TABLE IF NOT EXISTS review_report (
            report_id TEXT NOT NULL,
            report_version INTEGER NOT NULL,
            case_id TEXT NOT NULL,
            case_version INTEGER NOT NULL,
            owner_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            status TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            report_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (report_id, report_version),
            FOREIGN KEY (case_id, case_version)
                REFERENCES case_snapshot(case_id, version)
        );
        CREATE INDEX IF NOT EXISTS idx_review_report_owner
            ON review_report(owner_id, case_id, case_version);
        """
    )


class ReviewRepository:
    """Versioned persistence for immutable case snapshots and report drafts."""

    @staticmethod
    def save_case_snapshot(snapshot: CaseSnapshot) -> None:
        snapshot_json = _canonical_json(snapshot.model_dump(mode="json"))
        try:
            with get_connection() as conn:
                _ensure_schema(conn)
                conn.execute(
                    """
                    INSERT INTO case_snapshot
                        (case_id, owner_id, version, snapshot_json, captured_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot.case_id,
                        snapshot.owner_id,
                        snapshot.version,
                        snapshot_json,
                        snapshot.captured_at.isoformat(),
                    ),
                )
                conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ReviewStoreError("case_snapshot_version_already_exists") from exc

    @staticmethod
    def get_case_snapshot(
        case_id: str,
        version: int,
        owner_id: str,
    ) -> CaseSnapshot | None:
        with get_connection() as conn:
            _ensure_schema(conn)
            row = conn.execute(
                """
                SELECT snapshot_json
                FROM case_snapshot
                WHERE case_id = ? AND version = ? AND owner_id = ?
                """,
                (case_id, version, owner_id),
            ).fetchone()
        if row is None:
            return None
        return CaseSnapshot.model_validate_json(row[0])

    @staticmethod
    def save_report(report: ReviewReport, owner_id: str) -> str:
        with get_connection() as conn:
            _ensure_schema(conn)
            case_row = conn.execute(
                """
                SELECT 1
                FROM case_snapshot
                WHERE case_id = ? AND version = ? AND owner_id = ?
                """,
                (report.case_id, report.case_version, owner_id),
            ).fetchone()
            if case_row is None:
                raise ReviewStoreError("case_snapshot_not_found_or_not_owned")

            report_json = _canonical_json(report.model_dump(mode="json"))
            try:
                conn.execute(
                    """
                    INSERT INTO review_report
                        (report_id, report_version, case_id, case_version, owner_id,
                         run_id, status, content_hash, report_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        report.report_id,
                        report.version,
                        report.case_id,
                        report.case_version,
                        owner_id,
                        report.run_id,
                        report.status,
                        _content_hash(report),
                        report_json,
                        report.created_at.isoformat(),
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ReviewStoreError("report_version_already_exists") from exc
        return _content_hash(report)

    @staticmethod
    def get_report(
        report_id: str,
        report_version: int,
        owner_id: str,
    ) -> ReviewReport | None:
        with get_connection() as conn:
            _ensure_schema(conn)
            row = conn.execute(
                """
                SELECT report_json
                FROM review_report
                WHERE report_id = ? AND report_version = ? AND owner_id = ?
                """,
                (report_id, report_version, owner_id),
            ).fetchone()
        if row is None:
            return None
        return ReviewReport.model_validate_json(row[0])
