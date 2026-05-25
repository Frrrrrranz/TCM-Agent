from __future__ import annotations


TRACEABILITY_COLUMNS = {
    "source_file",
    "source_heading",
    "source_text",
    "source_hash",
    "parser_version",
    "review_status",
    "review_note",
}


def table_columns(db, table: str) -> set[str]:
    return {
        row["name"]
        for row in db.conn.execute(f"PRAGMA table_info({table})").fetchall()
    }


def test_structured_tables_have_traceability_columns(seeded_db) -> None:
    for table in ("herbs", "prescriptions", "syndromes", "acupoints"):
        assert TRACEABILITY_COLUMNS <= table_columns(seeded_db, table)


def test_seeded_records_are_traceable(seeded_db) -> None:
    rows = seeded_db.conn.execute(
        """
        SELECT name, source_file, source_heading, source_hash, parser_version, review_status
        FROM herbs
        WHERE name IN ('桂枝', '半夏', '附子')
        """
    ).fetchall()

    assert len(rows) == 3
    for row in rows:
        assert row["source_file"] == "seed_herbs.py"
        assert row["source_heading"] == row["name"]
        assert len(row["source_hash"]) == 64
        assert row["parser_version"] == "seed-v1"
        assert row["review_status"] == "approved"
