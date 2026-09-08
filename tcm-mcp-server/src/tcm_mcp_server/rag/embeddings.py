"""
Embedding 模型管理模块。

负责加载和管理中文 Embedding 模型（bge-large-zh-v1.5），
提供文本向量化能力，支持缓存以提升性能。
"""

from __future__ import annotations

import logging
from typing import Optional

from .embedding_contract import validate_embedding, validate_embeddings

logger = logging.getLogger(__name__)


class EmbeddingUnavailableError(RuntimeError):
    """Embedding 模型不可用，禁止静默降级为零向量。"""


class EmbeddingManager:
    """Embedding 模型管理器。"""

    DEFAULT_MODEL = "BAAI/bge-large-zh-v1.5"

    def __init__(self, model_name: str = DEFAULT_MODEL, device: Optional[str] = None) -> None:
        self.model_name = model_name
        self.device = device
        self._model = None
        self._dimension: int = 1024

    def _load_model(self) -> None:
        """延迟加载模型，加载失败时显式报错。"""
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer

            logger.info("正在加载 Embedding 模型: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name, device=self.device)
            model_dimension = self._model.get_sentence_embedding_dimension()
            if model_dimension is None:
                raise EmbeddingUnavailableError("模型未提供 embedding 维度")
            self._dimension = int(model_dimension)
            logger.info("Embedding 模型加载完成，向量维度: %d", self._dimension)
        except ImportError as exc:
            raise EmbeddingUnavailableError(
                "sentence-transformers 未安装，请先安装对应依赖"
            ) from exc
        except Exception as exc:
            logger.error("Embedding 模型加载失败: %s", exc)
            self._model = None
            if isinstance(exc, EmbeddingUnavailableError):
                raise
            raise EmbeddingUnavailableError(
                f"无法加载 embedding 模型: {self.model_name}"
            ) from exc

    @property
    def dimension(self) -> int:
        """获取向量维度。"""
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        """将单条文本转换为经过契约校验的向量。"""
        if self._model is None:
            self._load_model()

        embedding = self._model.encode(text, normalize_embeddings=True)
        values = embedding.tolist() if hasattr(embedding, "tolist") else embedding
        return validate_embedding(values, expected_dimension=self.dimension)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量将文本转换为经过契约校验的向量。"""
        if self._model is None:
            self._load_model()

        embeddings = self._model.encode(texts, normalize_embeddings=True)
        values = [
            embedding.tolist() if hasattr(embedding, "tolist") else embedding
            for embedding in embeddings
        ]
        return validate_embeddings(values, expected_dimension=self.dimension)

    def embed_query(self, query: str) -> list[float]:
        """将查询文本转换为带 BGE 检索前缀的向量。"""
        prefixed_query = f"为这个句子生成表示以用于检索相关文章：{query}"
        return self.embed_text(prefixed_query)
