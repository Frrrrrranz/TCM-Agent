"""向量索引 manifest，用于绑定模型、维度和来源版本。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class IndexManifestError(ValueError):
    """索引 manifest 缺失、损坏或与运行时契约不兼容。"""


@dataclass(frozen=True)
class IndexManifest:
    """一次完整索引构建的可验证描述。"""

    schema_version: str
    index_version: str
    embedding_model: str
    embedding_dimension: int
    collections: dict[str, int]
    dataset_versions: list[str]
    source_count: int
    created_at: str
    status: str = "staging"

    @classmethod
    def create(
        cls,
        *,
        index_version: str,
        embedding_model: str,
        embedding_dimension: int,
        collections: dict[str, int],
        dataset_versions: list[str],
        source_count: int,
        status: str = "staging",
    ) -> "IndexManifest":
        """创建带 UTC 时间戳的 manifest。"""
        return cls(
            schema_version="1",
            index_version=index_version,
            embedding_model=embedding_model,
            embedding_dimension=embedding_dimension,
            collections=dict(collections),
            dataset_versions=sorted(set(dataset_versions)),
            source_count=source_count,
            created_at=datetime.now(timezone.utc).isoformat(),
            status=status,
        )

    def validate(self, *, embedding_model: str, embedding_dimension: int) -> None:
        """校验 manifest 是否能被当前 embedding 配置使用。"""
        if self.schema_version != "1":
            raise IndexManifestError(
                f"不支持的 manifest schema_version: {self.schema_version}"
            )
        if self.status != "active":
            raise IndexManifestError(f"索引 manifest 未激活: status={self.status}")
        if self.embedding_model != embedding_model:
            raise IndexManifestError(
                "embedding 模型不匹配: "
                f"expected={embedding_model}, actual={self.embedding_model}"
            )
        if self.embedding_dimension != embedding_dimension:
            raise IndexManifestError(
                "embedding 维度不匹配: "
                f"expected={embedding_dimension}, actual={self.embedding_dimension}"
            )
        if self.source_count < 0 or any(count < 0 for count in self.collections.values()):
            raise IndexManifestError("manifest 中的数量不能为负数")

    def to_dict(self) -> dict[str, Any]:
        """转换为适合 JSON 持久化的字典。"""
        return asdict(self)

    def write(self, path: str | Path) -> None:
        """以稳定、可审计的 JSON 格式写入 manifest。"""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )

    @classmethod
    def read(cls, path: str | Path) -> "IndexManifest":
        """读取并进行基础结构校验。"""
        target = Path(path)
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
            manifest = cls(**payload)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise IndexManifestError(f"无法读取索引 manifest: {target}") from exc
        if not manifest.index_version or not manifest.embedding_model:
            raise IndexManifestError("manifest 缺少 index_version 或 embedding_model")
        return manifest
