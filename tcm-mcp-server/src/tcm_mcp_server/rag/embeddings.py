"""
Embedding 模型管理模块。

负责加载和管理中文 Embedding 模型（bge-large-zh-v1.5），
提供文本向量化能力，支持缓存以提升性能。
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """
    Embedding 模型管理器。

    封装 sentence-transformers 模型加载与文本向量化。
    支持延迟加载（lazy loading）和模型缓存。
    """

    # 默认使用 BAAI 的中文 Embedding 模型
    DEFAULT_MODEL = "BAAI/bge-large-zh-v1.5"

    def __init__(self, model_name: str = DEFAULT_MODEL, device: Optional[str] = None) -> None:
        """
        初始化 Embedding 管理器。

        Args:
            model_name: HuggingFace 模型名称或本地路径
            device: 运行设备（'cpu', 'cuda', 'mps'），None 表示自动选择
        """
        self.model_name = model_name
        self.device = device
        self._model = None
        self._dimension: int = 1024  # bge-large-zh-v1.5 的向量维度

    def _load_model(self) -> None:
        """延迟加载 Embedding 模型。"""
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer

            logger.info("正在加载 Embedding 模型: %s", self.model_name)
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
            )
            logger.info("Embedding 模型加载完成，向量维度: %d", self._dimension)
        except ImportError:
            logger.warning(
                "sentence-transformers 未安装，将使用轻量回退方案。"
                "请执行: pip install sentence-transformers"
            )
            self._model = None
        except Exception as exc:
            logger.error("Embedding 模型加载失败: %s", exc)
            self._model = None

    @property
    def dimension(self) -> int:
        """获取向量维度。"""
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        """
        将单条文本转换为向量。

        Args:
            text: 输入文本

        Returns:
            浮点数向量列表
        """
        if self._model is None:
            self._load_model()

        if self._model is None:
            # 回退：返回零向量
            logger.warning("使用零向量回退（模型未加载）")
            return [0.0] * self._dimension

        # bge 模型建议在 query 前加指令前缀
        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        批量将文本转换为向量。

        Args:
            texts: 输入文本列表

        Returns:
            向量列表
        """
        if self._model is None:
            self._load_model()

        if self._model is None:
            logger.warning("使用零向量回退（模型未加载）")
            return [[0.0] * self._dimension for _ in texts]

        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return [emb.tolist() for emb in embeddings]

    def embed_query(self, query: str) -> list[float]:
        """
        将查询文本转换为向量（带 query 前缀）。

        Args:
            query: 用户查询

        Returns:
            查询向量
        """
        # bge 模型在检索时建议为 query 添加指令前缀
        prefixed_query = f"为这个句子生成表示以用于检索相关文章：{query}"
        return self.embed_text(prefixed_query)
