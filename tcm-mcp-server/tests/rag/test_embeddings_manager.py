import pytest

from tcm_mcp_server.rag.embeddings import EmbeddingManager, EmbeddingUnavailableError


def test_embedding_manager_does_not_fallback_to_zero_vector(monkeypatch) -> None:
    manager = EmbeddingManager(model_name="missing-model")

    def fail_load() -> None:
        raise EmbeddingUnavailableError("model unavailable")

    monkeypatch.setattr(manager, "_load_model", fail_load)

    with pytest.raises(EmbeddingUnavailableError, match="model unavailable"):
        manager.embed_text("测试")
