from __future__ import annotations


def test_pipeline_maps_exact_record_to_row_level_evidence(pipeline) -> None:
    evidence = pipeline.evidence_for(
        "tcm_search_herb",
        {"name": "桂枝"},
    )

    assert evidence
    item = evidence[0]
    assert item.evidence_id.startswith("db:")
    assert len(item.source_hash) == 64
    assert item.source
    assert item.title
    assert item.retrieval_method == "exact"
    assert item.excerpt


def test_vector_index_preserves_traceability_metadata(seeded_vector_pipeline) -> None:
    results = seeded_vector_pipeline.retriever.vector_store.similarity_search(
        "syndromes",
        "头痛 发热",
        k=1,
    )

    assert results
    metadata = results[0]["metadata"]
    assert metadata["record_id"]
    assert len(metadata["source_hash"]) == 64
    assert metadata["source_file"]
    assert metadata["dataset_version"]
