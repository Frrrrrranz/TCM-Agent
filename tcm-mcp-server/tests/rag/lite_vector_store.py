"""
轻量级向量存储模拟。

使用 scikit-learn 的 TF-IDF + 余弦相似度替代 ChromaDB，
用于在 ChromaDB Rust 后端不可用的环境（如 Windows Anaconda）中
运行 RAG 评测。

NOTE: 这是测试专用的回退方案。生产环境仍使用 ChromaDB + bge-large-zh。
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class LiteVectorStore:
    """
    基于 TF-IDF 的轻量级向量存储。

    提供与 VectorStore 相同的 add_texts / similarity_search 接口，
    无需 ChromaDB 或 ONNX 模型。
    """

    def __init__(self) -> None:
        self._collections: dict[str, _Collection] = {}

    def add_texts(
        self,
        collection_name: str,
        texts: list[str],
        metadatas: Optional[list[dict]] = None,
        ids: Optional[list[str]] = None,
    ) -> None:
        """向指定集合添加文本。"""
        if collection_name not in self._collections:
            self._collections[collection_name] = _Collection()

        col = self._collections[collection_name]
        metas = metadatas or [{}] * len(texts)
        doc_ids = ids or [f"{collection_name}_{i}" for i in range(len(texts))]

        for doc_id, text, meta in zip(doc_ids, texts, metas):
            col.add(doc_id, text, meta)

        # 添加完毕后重建索引
        col.rebuild_index()
        logger.info("LiteVectorStore: 已向 '%s' 添加 %d 条文本", collection_name, len(texts))

    def similarity_search(
        self,
        collection_name: str,
        query: str,
        k: int = 10,
    ) -> list[dict]:
        """语义相似度检索（基于 TF-IDF 余弦相似度）。"""
        col = self._collections.get(collection_name)
        if col is None:
            return []
        return col.search(query, k)

    def count(self, collection_name: str) -> int:
        """获取集合中的文档数量。"""
        col = self._collections.get(collection_name)
        return len(col.documents) if col else 0

    def delete_collection(self, collection_name: str) -> None:
        """删除集合。"""
        self._collections.pop(collection_name, None)

    def list_collections(self) -> list[str]:
        """列出所有集合名称。"""
        return list(self._collections.keys())


class _Collection:
    """单个集合的内部实现。"""

    def __init__(self) -> None:
        self.documents: list[str] = []
        self.metadatas: list[dict] = []
        self.ids: list[str] = []
        self._vectorizer = None
        self._matrix = None

    def add(self, doc_id: str, text: str, metadata: dict) -> None:
        self.documents.append(text)
        self.metadatas.append(metadata)
        self.ids.append(doc_id)

    def rebuild_index(self) -> None:
        """使用中文字符级 TF-IDF 构建索引。"""
        if not self.documents:
            return

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            # NOTE: 使用字符级 n-gram (1-3) 作为中文分词的简易替代。
            # 对于中医术语（如"头痛"、"发热"、"脉浮缓"）效果足够。
            self._vectorizer = TfidfVectorizer(
                analyzer="char",
                ngram_range=(1, 3),
                max_features=5000,
            )
            self._matrix = self._vectorizer.fit_transform(self.documents)
        except ImportError:
            logger.warning("scikit-learn 未安装，使用关键词匹配回退")
            self._vectorizer = None
            self._matrix = None

    def search(self, query: str, k: int) -> list[dict]:
        """检索最相似的文档。"""
        if self._vectorizer is not None and self._matrix is not None:
            return self._search_tfidf(query, k)
        return self._search_keyword(query, k)

    def _search_tfidf(self, query: str, k: int) -> list[dict]:
        """TF-IDF 余弦相似度检索。"""
        from sklearn.metrics.pairwise import cosine_similarity

        query_vec = self._vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self._matrix).flatten()

        # 按相似度降序排列
        top_indices = similarities.argsort()[::-1][:k]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            results.append({
                "id": self.ids[idx],
                "document": self.documents[idx],
                "metadata": self.metadatas[idx],
                "distance": 1.0 - score,
                "score": score,
            })
        return results

    def _search_keyword(self, query: str, k: int) -> list[dict]:
        """关键词匹配回退（无 sklearn 时使用）。"""
        # 提取查询中的字符 2-gram
        query_chars = set()
        for i in range(len(query) - 1):
            query_chars.add(query[i:i + 2])
        if not query_chars:
            query_chars = set(query)

        scored = []
        for i, doc in enumerate(self.documents):
            doc_chars = set()
            for j in range(len(doc) - 1):
                doc_chars.add(doc[j:j + 2])
            overlap = len(query_chars & doc_chars)
            score = overlap / max(len(query_chars | doc_chars), 1)
            scored.append((i, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        results = []
        for idx, score in scored[:k]:
            results.append({
                "id": self.ids[idx],
                "document": self.documents[idx],
                "metadata": self.metadatas[idx],
                "distance": 1.0 - score,
                "score": score,
            })
        return results
