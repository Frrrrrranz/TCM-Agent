"""
ChromaDB 向量库封装模块。

提供中医药知识库的向量存储、检索和集合管理能力。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .embeddings import EmbeddingManager

logger = logging.getLogger(__name__)
CHROMA_MAX_BATCH_SIZE = 5000


class VectorStoreContractError(RuntimeError):
    """向量集合与当前 embedding 契约不兼容。"""


class VectorStore:
    """ChromaDB 向量数据库封装。"""

    def __init__(
        self,
        persist_dir: str | Path,
        *,
        ephemeral: bool = False,
        embedding_manager: EmbeddingManager | None = None,
        index_version: str = "index-v1",
    ) -> None:
        self.persist_dir = Path(persist_dir)
        self._ephemeral = ephemeral
        self.embedding_manager = embedding_manager
        self.index_version = index_version
        self._client = None
        self._collections: dict[str, object] = {}

    def _get_client(self):
        """延迟获取 ChromaDB 客户端。"""
        if self._client is not None:
            return self._client

        try:
            import chromadb

            if self._ephemeral:
                self._client = chromadb.EphemeralClient()
                logger.info("ChromaDB EphemeralClient 已初始化（内存模式）")
            else:
                self._client = chromadb.PersistentClient(path=str(self.persist_dir))
                logger.info("ChromaDB 客户端已初始化: %s", self.persist_dir)
        except ImportError:
            logger.warning("chromadb 未安装，向量检索功能不可用")
            self._client = None
        except Exception as exc:
            logger.error("ChromaDB 初始化失败: %s", exc)
            self._client = None

        return self._client

    def _collection_metadata(self) -> dict[str, str | int]:
        """返回新集合的 embedding 契约元数据。"""
        if self.embedding_manager is None:
            return {}
        return {
            "embedding_model": self.embedding_manager.model_name,
            "embedding_dimension": self.embedding_manager.dimension,
            "index_version": self.index_version,
        }

    def _validate_collection_contract(self, collection: object, name: str) -> None:
        """拒绝未声明或不匹配当前 embedding 的生产集合。"""
        if self.embedding_manager is None:
            return

        metadata = getattr(collection, "metadata", None) or {}
        expected = self._collection_metadata()
        missing = [key for key in expected if key not in metadata]
        if missing:
            raise VectorStoreContractError(
                f"集合 '{name}' 缺少 embedding 契约元数据: {', '.join(missing)}"
            )
        if metadata.get("embedding_model") != expected["embedding_model"]:
            raise VectorStoreContractError(
                f"集合 '{name}' 的 embedding 模型不匹配: "
                f"expected={expected['embedding_model']}, "
                f"actual={metadata.get('embedding_model')}"
            )
        if int(metadata["embedding_dimension"]) != expected["embedding_dimension"]:
            raise VectorStoreContractError(
                f"集合 '{name}' 的 embedding 维度不匹配: "
                f"expected={expected['embedding_dimension']}, "
                f"actual={metadata.get('embedding_dimension')}"
            )

    def _get_collection(self, name: str):
        """获取或创建集合，并校验 embedding 契约。"""
        client = self._get_client()
        if client is None:
            return None

        if name not in self._collections:
            try:
                collection = client.get_collection(name)
                logger.info("获取已有集合: %s", name)
            except Exception:
                collection = client.create_collection(
                    name,
                    metadata=self._collection_metadata() or None,
                )
                logger.info("创建新集合: %s", name)
            self._validate_collection_contract(collection, name)
            self._collections[name] = collection

        return self._collections[name]

    def add_texts(
        self,
        collection_name: str,
        texts: list[str],
        metadatas: Optional[list[dict]] = None,
        ids: Optional[list[str]] = None,
    ) -> None:
        """向指定集合添加文本，生产模式显式传入 embedding。"""
        if not texts:
            return
        collection = self._get_collection(collection_name)
        if collection is None:
            logger.warning("向量库不可用，跳过添加文本")
            return

        resolved_ids = ids or [f"{collection_name}_{i}" for i in range(len(texts))]
        resolved_metadatas = metadatas or [{} for _ in texts]
        if len(resolved_ids) != len(texts) or len(resolved_metadatas) != len(texts):
            raise ValueError("texts、metadatas、ids 的长度必须一致")

        for start in range(0, len(texts), CHROMA_MAX_BATCH_SIZE):
            end = start + CHROMA_MAX_BATCH_SIZE
            batch = {
                "documents": texts[start:end],
                "metadatas": resolved_metadatas[start:end],
                "ids": resolved_ids[start:end],
            }
            if self.embedding_manager is not None:
                batch["embeddings"] = self.embedding_manager.embed_texts(texts[start:end])
            collection.add(**batch)
        logger.info("已向集合 '%s' 添加 %d 条文本", collection_name, len(texts))

    def similarity_search(
        self,
        collection_name: str,
        query: str,
        k: int = 10,
    ) -> list[dict]:
        """语义相似度检索，生产模式显式传入 query embedding。"""
        collection = self._get_collection(collection_name)
        if collection is None:
            logger.warning("向量库不可用，返回空结果")
            return []

        query_kwargs = {"n_results": k}
        if self.embedding_manager is not None:
            query_kwargs["query_embeddings"] = [self.embedding_manager.embed_query(query)]
        else:
            query_kwargs["query_texts"] = [query]
        results = collection.query(**query_kwargs)

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0]

        return [
            {
                "id": ids[i] if i < len(ids) else "",
                "document": documents[i] if i < len(documents) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "distance": distances[i] if i < len(distances) else 0.0,
                "score": 1.0 - (distances[i] if i < len(distances) else 0.0),
            }
            for i in range(len(documents))
        ]

    def count(self, collection_name: str) -> int:
        """获取集合中的文档数量。"""
        collection = self._get_collection(collection_name)
        return 0 if collection is None else collection.count()

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
        return [collection.name for collection in client.list_collections()]
