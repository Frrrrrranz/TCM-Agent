"""
RAG 评测指标计算模块。

实现信息检索领域的标准评测指标：
- Recall@K：Top-K 命中率
- MRR (Mean Reciprocal Rank)：首个正确结果的排名倒数
- NDCG@K：带位置权重的归一化折损累计增益

所有函数均为纯函数，无外部依赖。
"""

from __future__ import annotations

import math
from typing import Optional


def recall_at_k(
    retrieved: list[str],
    relevant: set[str],
    k: int = 5,
) -> float:
    """
    计算 Recall@K。

    在 Top-K 检索结果中，命中的相关文档占全部相关文档的比例。

    Args:
        retrieved: 检索返回的文档名列表（按排名排序）
        relevant: 相关文档名集合（Ground Truth）
        k: 截断位置

    Returns:
        0.0 ~ 1.0 的浮点数
    """
    if not relevant:
        return 1.0  # 没有相关文档时视为全部命中

    top_k = retrieved[:k]
    hit_count = sum(1 for doc in top_k if doc in relevant)
    return hit_count / len(relevant)


def mrr(
    retrieved: list[str],
    relevant: set[str],
) -> float:
    """
    计算 MRR (Mean Reciprocal Rank)。

    第一个命中相关文档的排名倒数。
    若未命中任何相关文档，返回 0.0。

    Args:
        retrieved: 检索返回的文档名列表（按排名排序）
        relevant: 相关文档名集合（Ground Truth）

    Returns:
        0.0 ~ 1.0 的浮点数
    """
    for i, doc in enumerate(retrieved):
        if doc in relevant:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(
    retrieved: list[str],
    relevant: set[str],
    partially_relevant: Optional[set[str]] = None,
    k: int = 5,
) -> float:
    """
    计算 NDCG@K (Normalized Discounted Cumulative Gain)。

    使用三档相关性评分：
    - relevant（完全相关）: 2 分
    - partially_relevant（部分相关）: 1 分
    - 不相关: 0 分

    Args:
        retrieved: 检索返回的文档名列表（按排名排序）
        relevant: 完全相关文档名集合
        partially_relevant: 部分相关文档名集合
        k: 截断位置

    Returns:
        0.0 ~ 1.0 的浮点数
    """
    if not relevant and not (partially_relevant or set()):
        return 1.0

    partial = partially_relevant or set()

    def _relevance_score(doc: str) -> int:
        if doc in relevant:
            return 2
        if doc in partial:
            return 1
        return 0

    # DCG@K
    dcg = 0.0
    for i, doc in enumerate(retrieved[:k]):
        rel = _relevance_score(doc)
        if rel > 0:
            dcg += rel / math.log2(i + 2)  # i+2 因为位置从 1 开始

    # IDCG@K：理想排序（先 relevant，再 partially_relevant）
    ideal_scores = sorted(
        [2] * len(relevant) + [1] * len(partial),
        reverse=True,
    )[:k]

    idcg = 0.0
    for i, rel in enumerate(ideal_scores):
        if rel > 0:
            idcg += rel / math.log2(i + 2)

    if idcg == 0.0:
        return 0.0

    return dcg / idcg


def compute_batch_metrics(
    results: list[dict],
    k: int = 5,
) -> dict:
    """
    批量计算评测指标。

    Args:
        results: 评测结果列表，每项包含:
            - retrieved: list[str] — 检索到的文档名
            - relevant: set[str] — 完全相关文档名
            - partially_relevant: set[str] — 部分相关文档名（可选）
        k: 截断位置

    Returns:
        包含平均指标的字典:
        {
            "recall_at_k": float,
            "mrr": float,
            "ndcg_at_k": float,
            "total_cases": int,
            "hit_cases": int,  # 至少命中一个相关文档的用例数
        }
    """
    if not results:
        return {
            "recall_at_k": 0.0,
            "mrr": 0.0,
            "ndcg_at_k": 0.0,
            "total_cases": 0,
            "hit_cases": 0,
        }

    recalls = []
    mrrs = []
    ndcgs = []
    hit_count = 0

    for r in results:
        retrieved = r["retrieved"]
        rel = r["relevant"]
        partial = r.get("partially_relevant", set())

        recall_val = recall_at_k(retrieved, rel, k=k)
        mrr_val = mrr(retrieved, rel)
        ndcg_val = ndcg_at_k(retrieved, rel, partial, k=k)

        recalls.append(recall_val)
        mrrs.append(mrr_val)
        ndcgs.append(ndcg_val)

        if mrr_val > 0:
            hit_count += 1

    total = len(results)
    return {
        "recall_at_k": sum(recalls) / total,
        "mrr": sum(mrrs) / total,
        "ndcg_at_k": sum(ndcgs) / total,
        "total_cases": total,
        "hit_cases": hit_count,
    }
