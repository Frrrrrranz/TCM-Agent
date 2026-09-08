import pytest

from tcm_mcp_server.rag.vector_store import VectorStore, VectorStoreContractError


class FakeEmbeddingManager:
    model_name = "test-model"
    dimension = 2

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]

    def embed_query(self, query: str) -> list[float]:
        return [0.0, 1.0]


class FakeCollection:
    def __init__(self, metadata: dict) -> None:
        self.metadata = metadata
        self.add_calls: list[dict] = []
        self.query_calls: list[dict] = []

    def add(self, **kwargs) -> None:
        self.add_calls.append(kwargs)

    def query(self, **kwargs) -> dict:
        self.query_calls.append(kwargs)
        return {
            "documents": [["doc"]],
            "metadatas": [[{"source_file": "fixture.md"}]],
            "distances": [[0.2]],
            "ids": [["id-1"]],
        }

    def count(self) -> int:
        return 1


class FakeClient:
    def __init__(self, collection: FakeCollection | None = None) -> None:
        self.collection = collection

    def get_collection(self, name: str) -> FakeCollection:
        if self.collection is None:
            raise RuntimeError("not found")
        return self.collection

    def create_collection(self, name: str, metadata: dict | None = None) -> FakeCollection:
        self.collection = FakeCollection(metadata or {})
        return self.collection


def test_vector_store_passes_explicit_embeddings() -> None:
    store = VectorStore("unused", embedding_manager=FakeEmbeddingManager())
    client = FakeClient()
    store._client = client

    store.add_texts("herbs", ["黄芪"])
    result = store.similarity_search("herbs", "补气", k=1)

    assert client.collection is not None
    assert client.collection.add_calls[0]["embeddings"] == [[1.0, 0.0]]
    assert client.collection.query_calls[0]["query_embeddings"] == [[0.0, 1.0]]
    assert result[0]["metadata"]["source_file"] == "fixture.md"


def test_vector_store_rejects_collection_without_contract() -> None:
    store = VectorStore("unused", embedding_manager=FakeEmbeddingManager())
    store._client = FakeClient(FakeCollection({}))

    with pytest.raises(VectorStoreContractError, match="缺少 embedding 契约元数据"):
        store.similarity_search("herbs", "补气", k=1)
