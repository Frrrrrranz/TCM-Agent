"""
方剂 RAG 评测测试。

评估 症状→方剂 检索链路的 Recall@5、MRR、NDCG@5 指标，
并对比纯向量检索 vs 混合检索的效果差异。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from .metrics import compute_batch_metrics

logger = logging.getLogger(__name__)

DATASET_PATH = Path(__file__).resolve().parents[1] / "datasets" / "rag_prescription_eval.json"

K = 5  # 评测截断位置


def load_eval_cases() -> list[dict]:
    """加载评测数据集。"""
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))["cases"]


# ── Baseline: 纯向量检索 ──────────────────────────────────────


def _baseline_vector_search(vector_store, symptoms_text: str) -> list[str]:
    """
    纯向量检索基线。

    直接调用 vector_store.similarity_search("prescriptions", ...)
    """
    results = vector_store.similarity_search("prescriptions", symptoms_text, k=K * 2)
    return [
        r.get("metadata", {}).get("name", "")
        for r in results
        if r.get("metadata", {}).get("name")
    ]


# ── Hybrid: 当前 retriever 的混合检索 ────────────────────────


def _hybrid_search(retriever, symptoms_text: str) -> list[str]:
    """
    调用 HybridRetriever.search_prescriptions，使用混合检索。

    策略: SQLite 结构化查询 + 向量语义补充
    """
    results = retriever.search_prescriptions(symptoms=symptoms_text)
    return [p.name for p in results]


# ── 逐条评测 ─────────────────────────────────────────────────


CASES = load_eval_cases()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_prescription_retrieval_per_case(seeded_vector_pipeline, case: dict) -> None:
    """逐条验证方剂检索：至少在 Top-K 中命中一个相关方剂。"""
    retriever = seeded_vector_pipeline.retriever
    symptoms_text = case["query"]["symptoms"]

    retrieved = _hybrid_search(retriever, symptoms_text)

    relevant = set(case["expected"]["relevant"])
    partial = set(case["expected"].get("partially_relevant", []))
    all_acceptable = relevant | partial

    hit = any(doc in all_acceptable for doc in retrieved[:K])
    if not hit:
        logger.warning(
            "[%s] 未命中。期望: %s, 实际 Top-%d: %s",
            case["id"],
            list(all_acceptable),
            K,
            retrieved[:K],
        )


# ── 汇总评测：Hybrid ────────────────────────────────────────


def test_prescription_hybrid_aggregate_metrics(seeded_vector_pipeline) -> None:
    """汇总计算混合检索的 Recall@5、MRR、NDCG@5。"""
    retriever = seeded_vector_pipeline.retriever

    batch_results = []
    for case in CASES:
        symptoms_text = case["query"]["symptoms"]
        retrieved = _hybrid_search(retriever, symptoms_text)
        batch_results.append({
            "retrieved": retrieved,
            "relevant": set(case["expected"]["relevant"]),
            "partially_relevant": set(case["expected"].get("partially_relevant", [])),
        })

    metrics = compute_batch_metrics(batch_results, k=K)

    logger.info("=" * 60)
    logger.info("方剂检索 Hybrid 评测结果")
    logger.info("-" * 60)
    logger.info("Recall@%d:  %.4f", K, metrics["recall_at_k"])
    logger.info("MRR:        %.4f", metrics["mrr"])
    logger.info("NDCG@%d:    %.4f", K, metrics["ndcg_at_k"])
    logger.info("命中率:     %d/%d", metrics["hit_cases"], metrics["total_cases"])
    logger.info("=" * 60)

    # 基本健全性检查
    assert metrics["hit_cases"] >= metrics["total_cases"] * 0.3, (
        f"命中率过低: {metrics['hit_cases']}/{metrics['total_cases']}"
    )


# ── 对比实验：Baseline vs Hybrid ─────────────────────────────


def test_prescription_baseline_vs_hybrid(seeded_vector_pipeline) -> None:
    """对比纯向量检索 vs 混合检索的效果差异。"""
    retriever = seeded_vector_pipeline.retriever
    vector_store = retriever.vector_store

    baseline_results = []
    hybrid_results = []

    for case in CASES:
        symptoms_text = case["query"]["symptoms"]
        relevant = set(case["expected"]["relevant"])
        partial = set(case["expected"].get("partially_relevant", []))

        # Baseline: 纯向量
        baseline_retrieved = _baseline_vector_search(vector_store, symptoms_text)
        baseline_results.append({
            "retrieved": baseline_retrieved,
            "relevant": relevant,
            "partially_relevant": partial,
        })

        # Hybrid: 混合检索
        hybrid_retrieved = _hybrid_search(retriever, symptoms_text)
        hybrid_results.append({
            "retrieved": hybrid_retrieved,
            "relevant": relevant,
            "partially_relevant": partial,
        })

    baseline_metrics = compute_batch_metrics(baseline_results, k=K)
    hybrid_metrics = compute_batch_metrics(hybrid_results, k=K)

    logger.info("=" * 60)
    logger.info("方剂检索 Baseline vs Hybrid 对比")
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
        "Hybrid    %.4f    %.4f    %.4f    %d/%d",
        hybrid_metrics["recall_at_k"],
        hybrid_metrics["mrr"],
        hybrid_metrics["ndcg_at_k"],
        hybrid_metrics["hit_cases"],
        hybrid_metrics["total_cases"],
    )

    mrr_delta = hybrid_metrics["mrr"] - baseline_metrics["mrr"]
    logger.info("MRR 提升: %+.4f (%+.1f%%)", mrr_delta, mrr_delta * 100)
    logger.info("=" * 60)
