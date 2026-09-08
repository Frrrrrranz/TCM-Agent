import pytest

from tcm_mcp_server.rag.embedding_contract import (
    EmbeddingContractError,
    validate_embedding,
    validate_embeddings,
)


def test_validate_embedding_accepts_finite_vector() -> None:
    assert validate_embedding([0.1, 0.2], expected_dimension=2) == [0.1, 0.2]


@pytest.mark.parametrize(
    "vector",
    [
        [0.1],
        [0.0, 0.0],
        [float("nan"), 0.1],
        [float("inf"), 0.1],
    ],
)
def test_validate_embedding_rejects_invalid_output(vector: list[float]) -> None:
    with pytest.raises(EmbeddingContractError):
        validate_embedding(vector, expected_dimension=2)


def test_validate_embeddings_preserves_batch_shape() -> None:
    assert validate_embeddings([[1, 0], [0, 1]], expected_dimension=2) == [
        [1.0, 0.0],
        [0.0, 1.0],
    ]
