"""
混合检索引擎模块。

整合向量检索（ChromaDB 语义搜索）与 SQLite 精确查询，
提供统一的混合检索接口。
"""

from __future__ import annotations

import logging
from typing import Optional

from ..data.database import Database
from ..models.herb import Herb, HerbSearchParams
from ..models.prescription import Prescription, PrescriptionSearchParams
from ..models.syndrome import Syndrome, SyndromeSearchParams
from ..models.acupoint import Acupoint, AcupointSearchParams
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    混合检索引擎。

    根据查询类型自动选择检索策略：
    - 精确名称查询 → SQLite 精确匹配
    - 症状描述查询 → ChromaDB 语义检索 + SQLite 补全
    - 配伍禁忌 → 规则引擎
    """

    def __init__(self, db: Database, vector_store: VectorStore) -> None:
        """
        初始化混合检索引擎。

        Args:
            db: SQLite 数据库实例
            vector_store: ChromaDB 向量库实例
        """
        self.db = db
        self.vector_store = vector_store

    # ── 中药混合检索 ──────────────────────────────────────────

    def search_herbs(
        self,
        name: Optional[str] = None,
        nature: Optional[str] = None,
        taste: Optional[str] = None,
        meridian: Optional[str] = None,
        keywords: Optional[str] = None,
    ) -> list[Herb]:
        """
        中药混合检索。

        优先精确匹配名称，否则使用 SQLite 模糊查询 + 向量检索补充。
        """
        # 精确名称查询
        if name and not any([nature, taste, meridian, keywords]):
            herb = self.db.get_herb_by_name(name)
            return [herb] if herb else []

        # SQLite 结构化查询
        params = HerbSearchParams(
            name=name,
            nature=nature,
            taste=taste,
            meridian=meridian,
            keywords=keywords,
        )
        results = self.db.search_herbs(params)

        # 如果 SQLite 结果不足且有关键词，补充向量检索
        if len(results) < 5 and keywords:
            vector_results = self.vector_store.similarity_search(
                "herbs", keywords, k=5
            )
            # 合并去重
            existing_names = {h.name for h in results}
            for vr in vector_results:
                meta = vr.get("metadata", {})
                herb_name = meta.get("name", "")
                if herb_name and herb_name not in existing_names:
                    herb = self.db.get_herb_by_name(herb_name)
                    if herb:
                        results.append(herb)
                        existing_names.add(herb_name)

        return results

    # ── 方剂混合检索 ──────────────────────────────────────────

    def search_prescriptions(
        self,
        name: Optional[str] = None,
        syndrome: Optional[str] = None,
        symptoms: Optional[str] = None,
        herbs: Optional[str] = None,
    ) -> list[Prescription]:
        """
        方剂混合检索。

        症状→方剂匹配优先使用向量检索，名称查询使用 SQLite 精确匹配。
        """
        # 精确名称查询
        if name and not any([syndrome, symptoms, herbs]):
            pres = self.db.get_prescription_by_name(name)
            return [pres] if pres else []

        # SQLite 结构化查询
        params = PrescriptionSearchParams(
            name=name,
            syndrome=syndrome,
            symptoms=symptoms,
            herbs=herbs,
        )
        results = self.db.search_prescriptions(params)

        # 症状描述优先使用向量检索
        if symptoms and len(results) < 5:
            vector_results = self.vector_store.similarity_search(
                "prescriptions", symptoms, k=5
            )
            existing_names = {p.name for p in results}
            for vr in vector_results:
                meta = vr.get("metadata", {})
                pres_name = meta.get("name", "")
                if pres_name and pres_name not in existing_names:
                    pres = self.db.get_prescription_by_name(pres_name)
                    if pres:
                        results.append(pres)
                        existing_names.add(pres_name)

        return results

    # ── 证型混合检索 ──────────────────────────────────────────

    def search_syndromes(
        self,
        symptoms: list[str],
        tongue: Optional[str] = None,
        pulse: Optional[str] = None,
    ) -> list[dict]:
        """
        辨证分析检索。

        将症状组合为查询文本，通过向量检索匹配最相关的证型，
        再通过 SQLite 补全详细信息。
        """
        # 构建查询文本
        query_parts = symptoms.copy()
        if tongue:
            query_parts.append(f"舌象:{tongue}")
        if pulse:
            query_parts.append(f"脉象:{pulse}")
        query_text = "，".join(query_parts)

        # 向量检索
        vector_results = self.vector_store.similarity_search(
            "syndromes", query_text, k=10
        )

        # 重排序：优先匹配症状数量更多的证型
        scored_results = []
        for vr in vector_results:
            meta = vr.get("metadata", {})
            syndrome_name = meta.get("name", "")
            key_symptoms = meta.get("key_symptoms", "")

            # 计算症状匹配得分
            matched_count = sum(
                1 for s in symptoms if s in key_symptoms
            )
            match_ratio = matched_count / max(len(symptoms), 1)

            # 综合得分 = 语义相似度 * 0.6 + 症状匹配率 * 0.4
            combined_score = vr.get("score", 0) * 0.6 + match_ratio * 0.4

            # 从 SQLite 获取完整信息
            syndrome = None
            if syndrome_name:
                params = SyndromeSearchParams(name=syndrome_name)
                syndromes = self.db.search_syndromes(params)
                syndrome = syndromes[0] if syndromes else None

            if syndrome:
                scored_results.append({
                    "syndrome": syndrome,
                    "confidence": round(combined_score, 3),
                    "match_reason": f"匹配症状 {matched_count}/{len(symptoms)} 项",
                })

        # 按综合得分降序排列
        scored_results.sort(key=lambda x: x["confidence"], reverse=True)
        return scored_results[:5]

    # ── 医案检索 ──────────────────────────────────────────────

    def search_classic_cases(
        self,
        keywords: str,
        syndrome: Optional[str] = None,
    ) -> list[dict]:
        """
        医案检索。

        通过关键词在向量库中检索相关医案。
        """
        query = keywords
        if syndrome:
            query = f"{keywords} {syndrome}"

        results = self.vector_store.similarity_search(
            "classic_cases", query, k=5
        )
        return results

    # ── 配伍禁忌检查 ──────────────────────────────────────────

    def check_drug_interaction(self, herbs: list[str]) -> list[dict]:
        """
        配伍禁忌检查。

        使用规则引擎确定性检查，不依赖语义检索。
        """
        return self.db.check_drug_interaction(herbs)
