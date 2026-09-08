import pytest

from tcm_mcp_server.rag.index_manifest import IndexManifest, IndexManifestError


def make_manifest() -> IndexManifest:
    return IndexManifest.create(
        index_version="index-v1",
        embedding_model="test-model",
        embedding_dimension=2,
        collections={"herbs": 2, "prescriptions": 1},
        dataset_versions=["dataset-v1"],
        source_count=3,
        status="active",
    )


def test_manifest_round_trip(tmp_path) -> None:
    path = tmp_path / "index-manifest.json"
    manifest = make_manifest()
    manifest.write(path)

    loaded = IndexManifest.read(path)

    assert loaded == manifest
    loaded.validate(embedding_model="test-model", embedding_dimension=2)


def test_manifest_rejects_incompatible_runtime() -> None:
    with pytest.raises(IndexManifestError, match="embedding 模型不匹配"):
        make_manifest().validate(embedding_model="other-model", embedding_dimension=2)


def test_manifest_rejects_staging_index() -> None:
    staging = IndexManifest.create(
        index_version="index-v1",
        embedding_model="test-model",
        embedding_dimension=2,
        collections={},
        dataset_versions=[],
        source_count=0,
    )
    with pytest.raises(IndexManifestError, match="未激活"):
        staging.validate(embedding_model="test-model", embedding_dimension=2)
