"""
RAG 评测报告自动生成脚本。

运行完整评测流程并输出 Markdown 格式的评测报告。

用法:
    cd tcm-mcp-server
    python -m tests.rag.generate_report
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# NOTE: 确保 src 在 Python 路径中
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tcm_mcp_server.data.build_chroma import build_vector_store
from tcm_mcp_server.data.database import Database
from tcm_mcp_server.data.seed_acupoints import seed_acupoints
from tcm_mcp_server.data.seed_herbs import seed_herbs
from tcm_mcp_server.data.seed_prescriptions import seed_prescriptions
from tcm_mcp_server.data.seed_syndromes import seed_syndromes
from tcm_mcp_server.rag.retriever import HybridRetriever

from .lite_vector_store import LiteVectorStore

from .metrics import compute_batch_metrics

logger = logging.getLogger(__name__)

DATASETS_DIR = Path(__file__).resolve().parents[1] / "datasets"
REPORT_PATH = Path(__file__).resolve().parent / "evaluation_report.md"

K = 5


def _setup_pipeline(tmp_dir: Path) -> tuple[Database, HybridRetriever, LiteVectorStore]:
    """初始化数据库、种子数据和向量索引。"""
    db = Database(tmp_dir / "tcm.db")
    db.connect()
    seed_herbs(db)
    seed_prescriptions(db)
    seed_syndromes(db)
    seed_acupoints(db)

    # NOTE: 使用 TF-IDF 轻量级向量存储，规避 ChromaDB Windows 崩溃
    vector_store = LiteVectorStore()
    build_vector_store(db, vector_store)

    return db, HybridRetriever(db, vector_store), vector_store


def _eval_syndrome(retriever: HybridRetriever, vector_store: VectorStore) -> dict:
    """评测证型检索。"""
    data = json.loads(
        (DATASETS_DIR / "rag_syndrome_eval.json").read_text(encoding="utf-8")
    )
    cases = data["cases"]

    baseline_results = []
    reranked_results = []
    details = []

    for case in cases:
        query = case["query"]
        relevant = set(case["expected"]["relevant"])
        partial = set(case["expected"].get("partially_relevant", []))

        # Baseline: 纯向量
        query_parts = query["symptoms"].copy()
        if query.get("tongue"):
            query_parts.append(f"舌象:{query['tongue']}")
        if query.get("pulse"):
            query_parts.append(f"脉象:{query['pulse']}")
        query_text = "，".join(query_parts)

        baseline_raw = vector_store.similarity_search("syndromes", query_text, k=K * 2)
        baseline_retrieved = [
            r.get("metadata", {}).get("name", "")
            for r in baseline_raw
            if r.get("metadata", {}).get("name")
        ]

        # Reranked: 加权重排
        reranked_raw = retriever.search_syndromes(
            symptoms=query["symptoms"],
            tongue=query.get("tongue"),
            pulse=query.get("pulse"),
        )
        reranked_retrieved = [r["syndrome"].name for r in reranked_raw]

        baseline_results.append({
            "retrieved": baseline_retrieved,
            "relevant": relevant,
            "partially_relevant": partial,
        })
        reranked_results.append({
            "retrieved": reranked_retrieved,
            "relevant": relevant,
            "partially_relevant": partial,
        })

        # 逐条明细
        hit_baseline = any(d in relevant for d in baseline_retrieved[:K])
        hit_reranked = any(d in relevant for d in reranked_retrieved[:K])
        details.append({
            "id": case["id"],
            "description": case.get("description", ""),
            "expected": list(relevant),
            "baseline_top3": baseline_retrieved[:3],
            "reranked_top3": reranked_retrieved[:3],
            "hit_baseline": hit_baseline,
            "hit_reranked": hit_reranked,
        })

    return {
        "baseline": compute_batch_metrics(baseline_results, k=K),
        "reranked": compute_batch_metrics(reranked_results, k=K),
        "details": details,
    }


def _eval_prescription(retriever: HybridRetriever, vector_store: VectorStore) -> dict:
    """评测方剂检索。"""
    data = json.loads(
        (DATASETS_DIR / "rag_prescription_eval.json").read_text(encoding="utf-8")
    )
    cases = data["cases"]

    baseline_results = []
    hybrid_results = []
    details = []

    for case in cases:
        symptoms_text = case["query"]["symptoms"]
        relevant = set(case["expected"]["relevant"])
        partial = set(case["expected"].get("partially_relevant", []))

        # Baseline: 纯向量
        baseline_raw = vector_store.similarity_search("prescriptions", symptoms_text, k=K * 2)
        baseline_retrieved = [
            r.get("metadata", {}).get("name", "")
            for r in baseline_raw
            if r.get("metadata", {}).get("name")
        ]

        # Hybrid: 混合检索
        hybrid_raw = retriever.search_prescriptions(symptoms=symptoms_text)
        hybrid_retrieved = [p.name for p in hybrid_raw]

        baseline_results.append({
            "retrieved": baseline_retrieved,
            "relevant": relevant,
            "partially_relevant": partial,
        })
        hybrid_results.append({
            "retrieved": hybrid_retrieved,
            "relevant": relevant,
            "partially_relevant": partial,
        })

        hit_baseline = any(d in relevant for d in baseline_retrieved[:K])
        hit_hybrid = any(d in relevant for d in hybrid_retrieved[:K])
        details.append({
            "id": case["id"],
            "description": case.get("description", ""),
            "expected": list(relevant),
            "baseline_top3": baseline_retrieved[:3],
            "hybrid_top3": hybrid_retrieved[:3],
            "hit_baseline": hit_baseline,
            "hit_hybrid": hit_hybrid,
        })

    return {
        "baseline": compute_batch_metrics(baseline_results, k=K),
        "hybrid": compute_batch_metrics(hybrid_results, k=K),
        "details": details,
    }


def _format_report(syndrome_eval: dict, prescription_eval: dict) -> str:
    """生成 Markdown 格式的评测报告。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# RAG 评测报告",
        "",
        f"**生成时间**：{now}",
        f"**评测截断位置 (K)**：{K}",
        f"**Embedding 模型**：TF-IDF 字符级 n-gram（测试环境）/ bge-large-zh-v1.5（生产环境）",
        f"**数据规模**：18 个证型 / 14 个方剂",
        "",
        "---",
        "",
        "## 一、证型检索评测（症状→证型）",
        "",
        "### 指标汇总",
        "",
        f"| 指标 | Baseline（纯向量） | Reranked（加权重排） | 提升 |",
        f"|------|-------------------|---------------------|------|",
    ]

    sb = syndrome_eval["baseline"]
    sr = syndrome_eval["reranked"]

    def _delta(a: float, b: float) -> str:
        d = a - b
        if d == 0:
            return "—"
        return f"{d:+.1%}"

    lines.append(
        f"| Recall@{K} | {sb['recall_at_k']:.4f} | {sr['recall_at_k']:.4f} | {_delta(sr['recall_at_k'], sb['recall_at_k'])} |"
    )
    lines.append(
        f"| MRR | {sb['mrr']:.4f} | {sr['mrr']:.4f} | {_delta(sr['mrr'], sb['mrr'])} |"
    )
    lines.append(
        f"| NDCG@{K} | {sb['ndcg_at_k']:.4f} | {sr['ndcg_at_k']:.4f} | {_delta(sr['ndcg_at_k'], sb['ndcg_at_k'])} |"
    )
    lines.append(
        f"| 命中率 | {sb['hit_cases']}/{sb['total_cases']} | {sr['hit_cases']}/{sr['total_cases']} | — |"
    )

    lines.extend([
        "",
        "### 逐条明细",
        "",
        "| ID | 描述 | 期望 | Baseline Top-3 | Reranked Top-3 | B命中 | R命中 |",
        "|-----|------|------|---------------|---------------|-------|-------|",
    ])
    for d in syndrome_eval["details"]:
        lines.append(
            f"| {d['id']} | {d['description'][:20]} | {', '.join(d['expected'])} | "
            f"{', '.join(d['baseline_top3'][:3])} | {', '.join(d['reranked_top3'][:3])} | "
            f"{'✅' if d['hit_baseline'] else '❌'} | {'✅' if d['hit_reranked'] else '❌'} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 二、方剂检索评测（症状→方剂）",
        "",
        "### 指标汇总",
        "",
        f"| 指标 | Baseline（纯向量） | Hybrid（混合检索） | 提升 |",
        f"|------|-------------------|-------------------|------|",
    ])

    pb = prescription_eval["baseline"]
    ph = prescription_eval["hybrid"]

    lines.append(
        f"| Recall@{K} | {pb['recall_at_k']:.4f} | {ph['recall_at_k']:.4f} | {_delta(ph['recall_at_k'], pb['recall_at_k'])} |"
    )
    lines.append(
        f"| MRR | {pb['mrr']:.4f} | {ph['mrr']:.4f} | {_delta(ph['mrr'], pb['mrr'])} |"
    )
    lines.append(
        f"| NDCG@{K} | {pb['ndcg_at_k']:.4f} | {ph['ndcg_at_k']:.4f} | {_delta(ph['ndcg_at_k'], pb['ndcg_at_k'])} |"
    )
    lines.append(
        f"| 命中率 | {pb['hit_cases']}/{pb['total_cases']} | {ph['hit_cases']}/{ph['total_cases']} | — |"
    )

    lines.extend([
        "",
        "### 逐条明细",
        "",
        "| ID | 描述 | 期望 | Baseline Top-3 | Hybrid Top-3 | B命中 | H命中 |",
        "|-----|------|------|---------------|-------------|-------|-------|",
    ])
    for d in prescription_eval["details"]:
        lines.append(
            f"| {d['id']} | {d['description'][:20]} | {', '.join(d['expected'])} | "
            f"{', '.join(d['baseline_top3'][:3])} | {', '.join(d['hybrid_top3'][:3])} | "
            f"{'✅' if d['hit_baseline'] else '❌'} | {'✅' if d['hit_hybrid'] else '❌'} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 三、结论",
        "",
        f"1. 证型检索 Rerank（语义 × 0.6 + 症状匹配 × 0.4）相比纯向量，MRR 变化 {_delta(sr['mrr'], sb['mrr'])}",
        f"2. 方剂混合检索（SQLite + 向量补充）相比纯向量，MRR 变化 {_delta(ph['mrr'], pb['mrr'])}",
        f"3. 当前数据规模较小（18 证型 / 14 方剂），扩充数据后预期指标会进一步提升",
        "",
        "> **注意**：测试环境使用 TF-IDF 字符级 n-gram 作为向量化方案，",
        "> 生产环境切换 ChromaDB + `BAAI/bge-large-zh-v1.5` 后效果预期更优。",
    ])

    return "\n".join(lines)


def main() -> None:
    """运行评测并生成报告。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    import tempfile

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        tmp_path = Path(tmp_dir)
        logger.info("初始化评测环境...")
        db, retriever, vector_store = _setup_pipeline(tmp_path)

        logger.info("评测证型检索...")
        syndrome_eval = _eval_syndrome(retriever, vector_store)

        logger.info("评测方剂检索...")
        prescription_eval = _eval_prescription(retriever, vector_store)

        # NOTE: 显式关闭数据库，避免 Windows 上 TemporaryDirectory 清理失败
        db.close()

    report = _format_report(syndrome_eval, prescription_eval)
    REPORT_PATH.write_text(report, encoding="utf-8")
    logger.info("评测报告已生成: %s", REPORT_PATH)
    # NOTE: Windows 控制台默认 GBK 编码，无法打印 ✅/❌ emoji，用 replace 降级
    sys.stdout.buffer.write(report.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
