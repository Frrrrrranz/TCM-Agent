"""
ChromaDB 向量库封装模块。

提供中医药知识库的向量存储、检索和集合管理能力。
"""

from __future__ import annotations

import logging
import json
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class VectorStore:
    """
    ChromaDB 向量数据库封装。

    管理多个集合（collections），支持文本的向量化存储与语义检索。
    """

    def __init__(self, persist_dir: str | Path) -> None:
        """
        初始化向量库。

        Args:
            persist_dir: ChromaDB 持久化目录
        """
        self.persist_dir = Path(persist_dir)
        self._client = None
        self._collections: dict[str, object] = {}

    def _get_client(self):
        """延迟获取 ChromaDB 客户端。"""
        if self._client is not None:
            return self._client

        try:
            import chromadb
            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
            )
            logger.info("ChromaDB 客户端已初始化: %s", self.persist_dir)
        except ImportError:
            logger.warning("chromadb 未安装，向量检索功能不可用")
            self._client = None
        except Exception as exc:
            logger.error("ChromaDB 初始化失败: %s", exc)
            self._client = None

        return self._client

    def _get_collection(self, name: str):
        """获取或创建集合。"""
        client = self._get_client()
        if client is None:
            return None

        if name not in self._collections:
            try:
                collection = client.get_collection(name)
                self._collections[name] = collection
                logger.info("获取已有集合: %s", name)
            except Exception:
                collection = client.create_collection(name)
                self._collections[name] = collection
                logger.info("创建新集合: %s", name)

        return self._collections[name]

    def add_texts(
        self,
        collection_name: str,
        texts: list[str],
        metadatas: Optional[list[dict]] = None,
        ids: Optional[list[str]] = None,
    ) -> None:
        """
        向指定集合添加文本。

        Args:
            collection_name: 集合名称
            texts: 文本列表
            metadatas: 元数据列表
            ids: ID 列表（自动生成若为 None）
        """
        collection = self._get_collection(collection_name)
        if collection is None:
            logger.warning("向量库不可用，跳过添加文本")
            return

        if ids is None:
            ids = [f"{collection_name}_{i}" for i in range(len(texts))]

        collection.add(
            documents=texts,
            metadatas=metadatas or [{}] * len(texts),
            ids=ids,
        )
        logger.info("已向集合 '%s' 添加 %d 条文本", collection_name, len(texts))

    def similarity_search(
        self,
        collection_name: str,
        query: str,
        k: int = 10,
    ) -> list[dict]:
        """
        语义相似度检索。

        Args:
            collection_name: 集合名称
            query: 查询文本
            k: 返回结果数量

        Returns:
            检索结果列表，每项包含 document、metadata、distance
        """
        collection = self._get_collection(collection_name)
        if collection is None:
            logger.warning("向量库不可用，返回空结果")
            return []

        results = collection.query(
            query_texts=[query],
            n_results=k,
        )

        # 整理返回格式
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0]

        formatted = []
        for i in range(len(documents)):
            formatted.append({
                "id": ids[i] if i < len(ids) else "",
                "document": documents[i] if i < len(documents) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "distance": distances[i] if i < len(distances) else 0.0,
                "score": 1.0 - (distances[i] if i < len(distances) else 0.0),
            })

        return formatted

    def count(self, collection_name: str) -> int:
        """获取集合中的文档数量。"""
        collection = self._get_collection(collection_name)
        if collection is None:
            return 0
        return collection.count()

    def delete_collection(self, collection_name: str) -> None:
        """删除集合。"""
        client = self._get_client()
        if client is None:
            return
        try:
            client.delete_collection(collection_name)
            self._collections.pop(collection_name, None)
            logger.info("已删除集合: %s", collection_name)
        except Exception as exc:
            logger.warning("删除集合失败: %s", exc)

    def list_collections(self) -> list[str]:
        """列出所有集合名称。"""
        client = self._get_client()
        if client is None:
            return []
        collections = client.list_collections()
        return [col.name for col in collections]
