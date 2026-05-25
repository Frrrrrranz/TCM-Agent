"""
LangChain RAG 管线模块。

实现完整的 RAG 检索流程：
Query 改写 → 向量检索 → 重排序 → 结构化补全 → 结果组装
"""

from __future__ import annotations

import logging
from typing import Optional

from .retriever import HybridRetriever

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    RAG 检索管线。

    提供端到端的检索流程编排，支持查询改写、混合检索、
    结果重排序和格式化输出。
    """

    def __init__(self, retriever: HybridRetriever) -> None:
        """
        初始化 RAG 管线。

        Args:
            retriever: 混合检索引擎实例
        """
        self.retriever = retriever

    # ── 中药查询管线 ──────────────────────────────────────────

    async def search_herb(
        self,
        name: Optional[str] = None,
        nature: Optional[str] = None,
        taste: Optional[str] = None,
        meridian: Optional[str] = None,
        keywords: Optional[str] = None,
    ) -> str:
        """
        中药查询管线。

        返回格式化的 Markdown 结果。
        """
        herbs = self.retriever.search_herbs(
            name=name,
            nature=nature,
            taste=taste,
            meridian=meridian,
            keywords=keywords,
        )

        if not herbs:
            return "未找到匹配的中药信息。"

        # 格式化输出
        lines = [f"## 中药查询结果\n"]
        for herb in herbs:
            lines.append(f"### {herb.name}（{herb.pinyin}）")
            lines.append(f"- **分类**：{herb.category}")
            lines.append(f"- **四气**：{herb.nature}")
            lines.append(f"- **五味**：{herb.taste}")
            lines.append(f"- **归经**：{herb.meridian}")
            lines.append(f"- **毒性**：{herb.toxicity}")
            lines.append(f"- **功效**：{herb.effect}")
            lines.append(f"- **主治**：{herb.indication}")
            if herb.usage:
                lines.append(f"- **用法用量**：{herb.usage}")
            if herb.caution:
                lines.append(f"- **使用注意**：{herb.caution}")
            lines.append("")

        return "\n".join(lines)

    # ── 方剂查询管线 ──────────────────────────────────────────

    async def search_prescription(
        self,
        name: Optional[str] = None,
        syndrome: Optional[str] = None,
        symptoms: Optional[str] = None,
        herbs: Optional[str] = None,
    ) -> str:
        """
        方剂查询管线。

        返回格式化的 Markdown 结果。
        """
        prescriptions = self.retriever.search_prescriptions(
            name=name,
            syndrome=syndrome,
            symptoms=symptoms,
            herbs=herbs,
        )

        if not prescriptions:
            return "未找到匹配的方剂信息。"

        lines = [f"## 方剂查询结果\n"]
        for pres in prescriptions:
            lines.append(f"### {pres.name}")
            if pres.source:
                lines.append(f"- **出处**：{pres.source}")
            lines.append(f"- **分类**：{pres.category}")
            lines.append(f"- **组成**：{pres.composition}")
            lines.append(f"- **功用**：{pres.effect}")
            lines.append(f"- **主治**：{pres.indication}")
            if pres.syndrome:
                lines.append(f"- **证型**：{pres.syndrome}")
            if pres.symptoms:
                lines.append(f"- **典型症状**：{pres.symptoms}")
            if pres.explanation:
                lines.append(f"- **方解**：{pres.explanation}")
            if pres.addition:
                lines.append(f"- **加减化裁**：{pres.addition}")
            if pres.caution:
                lines.append(f"- **使用注意**：{pres.caution}")
            lines.append("")

        return "\n".join(lines)

    # ── 辨证分析管线 ──────────────────────────────────────────

    async def diagnose_syndrome(
        self,
        symptoms: list[str],
        tongue: Optional[str] = None,
        pulse: Optional[str] = None,
    ) -> str:
        """
        辨证分析管线。

        症状输入 → 向量检索 → 重排序 → 格式化输出。
        """
        results = self.retriever.search_syndromes(
            symptoms=symptoms,
            tongue=tongue,
            pulse=pulse,
        )

        if not results:
            return "未找到匹配的证型信息。建议咨询专业中医师进行辨证。"

        lines = ["## 辨证分析结果\n"]
        lines.append(f"**输入症状**：{'、'.join(symptoms)}")
        if tongue:
            lines.append(f"**舌象**：{tongue}")
        if pulse:
            lines.append(f"**脉象**：{pulse}")
        lines.append("")

        for i, result in enumerate(results, 1):
            syndrome = result["syndrome"]
            confidence = result["confidence"]
            match_reason = result["match_reason"]

            lines.append(f"### {i}. {syndrome.name}")
            lines.append(f"- **置信度**：{confidence:.1%}")
            lines.append(f"- **匹配依据**：{match_reason}")
            lines.append(f"- **辨证分类**：{syndrome.category}")
            lines.append(f"- **关键症状**：{syndrome.key_symptoms}")
            if syndrome.tongue:
                lines.append(f"- **舌象**：{syndrome.tongue}")
            if syndrome.pulse:
                lines.append(f"- **脉象**：{syndrome.pulse}")
            if syndrome.mechanism:
                lines.append(f"- **病机**：{syndrome.mechanism}")
            if syndrome.treatment_principle:
                lines.append(f"- **治法**：{syndrome.treatment_principle}")
            lines.append("")

        lines.append("---")
        lines.append("> **免责声明**：以上辨证分析仅供参考，不能替代专业中医师的诊断。")

        return "\n".join(lines)

    # ── 配伍禁忌检查管线 ──────────────────────────────────────

    async def check_drug_interaction(self, herbs: list[str]) -> str:
        """
        配伍禁忌检查管线。

        确定性规则检查，返回格式化结果。
        """
        conflicts = self.retriever.check_drug_interaction(herbs)

        lines = ["## 配伍禁忌检查结果\n"]
        lines.append(f"**检查药物**：{'、'.join(herbs)}\n")

        if not conflicts:
            lines.append("[通过] 未发现配伍禁忌。")
            return "\n".join(lines)

        for conflict in conflicts:
            severity_label = "[严重]" if conflict["severity"] == "error" else "[警告]"
            lines.append(f"{severity_label} **{conflict['type']}**")
            lines.append(f"   {conflict['description']}")
            lines.append("")

        lines.append("---")
        lines.append("> **安全提示**：配伍禁忌仅供参考，实际用药请遵医嘱。")

        return "\n".join(lines)

    # ── 穴位查询管线 ──────────────────────────────────────────

    async def search_acupoint(
        self,
        name: Optional[str] = None,
        meridian: Optional[str] = None,
        keywords: Optional[str] = None,
    ) -> str:
        """
        穴位查询管线。

        返回格式化的 Markdown 结果。
        """
        from ..models.acupoint import AcupointSearchParams

        params = AcupointSearchParams(
            name=name,
            meridian=meridian,
            keywords=keywords,
        )
        acupoints = self.retriever.db.search_acupoints(params)

        if not acupoints:
            return "未找到匹配的穴位信息。"

        lines = ["## 穴位查询结果\n"]
        for acupoint in acupoints:
            lines.append(f"### {acupoint.name}（{acupoint.pinyin}）")
            lines.append(f"- **归经**：{acupoint.meridian}")
            lines.append(f"- **定位**：{acupoint.location}")
            lines.append(f"- **主治**：{acupoint.indication}")
            if acupoint.operation:
                lines.append(f"- **操作**：{acupoint.operation}")
            if acupoint.caution:
                lines.append(f"- **注意事项**：{acupoint.caution}")
            lines.append("")

        return "\n".join(lines)

    # ── 医案检索管线 ──────────────────────────────────────────

    async def search_classic_case(
        self,
        keywords: str,
        syndrome: Optional[str] = None,
    ) -> str:
        """
        医案检索管线。

        返回格式化的 Markdown 结果。
        """
        results = self.retriever.search_classic_cases(
            keywords=keywords,
            syndrome=syndrome,
        )

        if not results:
            return "未找到匹配的医案信息。"

        lines = ["## 医案检索结果\n"]
        for i, result in enumerate(results, 1):
            doc = result.get("document", "")
            meta = result.get("metadata", {})
            score = result.get("score", 0)

            lines.append(f"### {i}. {meta.get('title', f'医案 {i}')}")
            lines.append(f"- **相关度**：{score:.1%}")
            if meta.get("source"):
                lines.append(f"- **来源**：{meta['source']}")
            lines.append("")
            lines.append(doc[:500] + ("..." if len(doc) > 500 else ""))
            lines.append("")

        return "\n".join(lines)
