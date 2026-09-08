"""Embedding 向量契约与运行时校验。"""

from __future__ import annotations

import math
from collections.abc import Sequence


class EmbeddingContractError(ValueError):
    """Embedding 模型输出不满足索引契约时抛出。"""


def validate_embedding(
    vector: Sequence[float],
    *,
    expected_dimension: int,
    name: str = "embedding",
) -> list[float]:
    """校验维度、数值有效性，并拒绝静默产生的零向量。"""
    if expected_dimension <= 0:
        raise EmbeddingContractError("expected_dimension 必须为正整数")
    if not isinstance(vector, Sequence) or isinstance(vector, (str, bytes)):
        raise EmbeddingContractError(f"{name} 必须是数值序列")
    if len(vector) != expected_dimension:
        raise EmbeddingContractError(
            f"{name} 维度不匹配: expected={expected_dimension}, actual={len(vector)}"
        )

    values: list[float] = []
    for index, value in enumerate(vector):
        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as exc:
            raise EmbeddingContractError(
                f"{name}[{index}] 不是可转换为 float 的数值"
            ) from exc
        if not math.isfinite(numeric_value):
            raise EmbeddingContractError(f"{name}[{index}] 不是有限数值")
        values.append(numeric_value)

    if all(value == 0.0 for value in values):
        raise EmbeddingContractError(f"{name} 不得为全零向量")
    return values


def validate_embeddings(
    vectors: Sequence[Sequence[float]],
    *,
    expected_dimension: int,
    name: str = "embeddings",
) -> list[list[float]]:
    """批量校验 embedding 输出，并保留稳定的 list[list[float]] 类型。"""
    return [
        validate_embedding(
            vector,
            expected_dimension=expected_dimension,
            name=f"{name}[{index}]",
        )
        for index, vector in enumerate(vectors)
    ]
