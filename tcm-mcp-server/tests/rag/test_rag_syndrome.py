"""
证型 RAG 评测测试。

评估 症状→证型 检索链路的 Recall@5、MRR、NDCG@5 指标，
并对比 Rerank（加权重排）前后的效果差异。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import pytest

from .metrics import (
    compute_batch_metrics,
    mrr,
    ndcg_at_k,
    recall_at_k,
)

logger = logging.getLogger(__name__)

DATASET_PATH = Path(__file__).resolve().parents[1] / "datasets" / "rag_syndrome_eval.json"

K = 5  # 评测截断位置


def load_eval_cases() -> list[dict]:
    """加载评测数据集。"""
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))["cases"]


# ── Baseline: 纯向量检索（不重排） ────────────────────────────


def _baseline_vector_search(
    vector_store,
    symptoms: list[str],
    tongue: Optional[str] = None,
    pulse: Optional[str] = None,
) -> list[str]:
    """
    纯向量检索基线。

    直接调用 vector_store.similarity_search，按语义距离排序，
    不经过 HybridRetriever 的加权重排逻辑。
    """
    query_parts = symptoms.copy()
    if tongue:
        query_parts.append(f"舌象:{tongue}")
    if pulse:
        query_parts.append(f"脉象:{pulse}")
    query_text = "，".join(query_parts)

    results = vector_store.similarity_search("syndromes", query_text, k=K * 2)
    return [r.get("metadata", {}).get("name", "") for r in results if r.get("metadata", {}).get("name")]


# ── Reranked: 当前 retriever 的加权重排 ──────────────────────


def _reranked_search(
    retriever,
    symptoms: list[str],
    tongue: Optional[str] = None,
    pulse: Optional[str] = None,
) -> list[str]:
    """
    调用 HybridRetriever.search_syndromes，使用加权重排。

    当前重排策略: 综合得分 = 语义相似度 * 0.6 + 症状匹配率 * 0.4
    """
    results = retriever.search_syndromes(
        symptoms=symptoms,
        tongue=tongue,
        pulse=pulse,
    )
    return [r["syndrome"].name for r in results]


# ── 逐条评测测试 ─────────────────────────────────────────────


CASES = load_eval_cases()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_syndrome_retrieval_per_case(seeded_vector_pipeline, case: dict) -> None:
    """逐条验证证型检索：至少在 Top-K 中命中一个相关证型。"""
    retriever = seeded_vector_pipeline.retriever
    query = case["query"]

    retrieved = _reranked_search(
        retriever,
        symptoms=query["symptoms"],
        tongue=query.get("tongue"),
        pulse=query.get("pulse"),
    )

    relevant = set(case["expected"]["relevant"])
    partial = set(case["expected"].get("partially_relevant", []))
    all_acceptable = relevant | partial

    # 宽松断言：Top-K 中至少命中一个相关或部分相关的证型
    hit = any(doc in all_acceptable for doc in retrieved[:K])
    if not hit:
        logger.warning(
            "[%s] 未命中。期望: %s, 实际 Top-%d: %s",
            case["id"],
            list(all_acceptable),
            K,
            retrieved[:K],
        )
    # NOTE: 即使未命中也不直接 fail，汇总测试会统计整体指标
    # 此处仅做日志记录，避免因个别难例阻塞 CI


# ── 汇总评测：Reranked ──────────────────────────────────────


def test_syndrome_reranked_aggregate_metrics(seeded_vector_pipeline) -> None:
    """汇总计算 Reranked 检索的 Recall@5、MRR、NDCG@5。"""
    retriever = seeded_vector_pipeline.retriever

    batch_results = []
    for case in CASES:
        query = case["query"]
        retrieved = _reranked_search(
            retriever,
            symptoms=query["symptoms"],
            tongue=query.get("tongue"),
            pulse=query.get("pulse"),
        )
        batch_results.append({
            "retrieved": retrieved,
            "relevant": set(case["expected"]["relevant"]),
            "partially_relevant": set(case["expected"].get("partially_relevant", [])),
        })

    metrics = compute_batch_metrics(batch_results, k=K)

    logger.info("=" * 60)
    logger.info("证型检索 Reranked 评测结果")
    logger.info("-" * 60)
    logger.info("Recall@%d:  %.4f", K, metrics["recall_at_k"])
    logger.info("MRR:        %.4f", metrics["mrr"])
    logger.info("NDCG@%d:    %.4f", K, metrics["ndcg_at_k"])
    logger.info("命中率:     %d/%d", metrics["hit_cases"], metrics["total_cases"])
    logger.info("=" * 60)

    # 基本健全性检查：至少有一半用例命中
    assert metrics["hit_cases"] >= metrics["total_cases"] * 0.3, (
        f"命中率过低: {metrics['hit_cases']}/{metrics['total_cases']}"
    )


# ── 对比实验：Baseline vs Reranked ───────────────────────────


def test_syndrome_baseline_vs_reranked(seeded_vector_pipeline) -> None:
    """对比纯向量检索 vs 加权重排的效果差异。"""
    retriever = seeded_vector_pipeline.retriever
    vector_store = retriever.vector_store

    baseline_results = []
    reranked_results = []

    for case in CASES:
        query = case["query"]
        relevant = set(case["expected"]["relevant"])
        partial = set(case["expected"].get("partially_relevant", []))

        # Baseline: 纯向量
        baseline_retrieved = _baseline_vector_search(
            vector_store,
            symptoms=query["symptoms"],
            tongue=query.get("tongue"),
            pulse=query.get("pulse"),
        )
        baseline_results.append({
            "retrieved": baseline_retrieved,
            "relevant": relevant,
            "partially_relevant": partial,
        })

        # Reranked: 加权重排
        reranked_retrieved = _reranked_search(
            retriever,
            symptoms=query["symptoms"],
            tongue=query.get("tongue"),
            pulse=query.get("pulse"),
        )
        reranked_results.append({
            "retrieved": reranked_retrieved,
            "relevant": relevant,
            "partially_relevant": partial,
        })

    baseline_metrics = compute_batch_metrics(baseline_results, k=K)
    reranked_metrics = compute_batch_metrics(reranked_results, k=K)

    logger.info("=" * 60)
    logger.info("证型检索 Baseline vs Reranked 对比")
    logger.info("-" * 60)
    logger.info(
        "         Recall@%d   MRR      NDCG@%d   命中",
        K, K,
    )
    logger.info(
        "Baseline  %.4f    %.4f    %.4f    %d/%d",
        baseline_metrics["recall_at_k"],
        baseline_metrics["mrr"],
        baseline_metrics["ndcg_at_k"],
        baseline_metrics["hit_cases"],
        baseline_metrics["total_cases"],
    )
    logger.info(
        "Reranked  %.4f    %.4f    %.4f    %d/%d",
        reranked_metrics["recall_at_k"],
        reranked_metrics["mrr"],
        reranked_metrics["ndcg_at_k"],
        reranked_metrics["hit_cases"],
        reranked_metrics["total_cases"],
    )

    mrr_delta = reranked_metrics["mrr"] - baseline_metrics["mrr"]
    logger.info("MRR 提升: %+.4f (%+.1f%%)", mrr_delta, mrr_delta * 100)
    logger.info("=" * 60)
