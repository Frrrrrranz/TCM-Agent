from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DataPaths:
    """Single source of truth for runtime data and imported source files."""

    data_dir: Path
    source_dir: Path

    @property
    def db_path(self) -> Path:
        return self.data_dir / "tcm.db"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def review_dir(self) -> Path:
        return self.data_dir / "review_queue"

    @property
    def summary_path(self) -> Path:
        return self.data_dir / "batch_import_summary.json"


def get_data_paths() -> DataPaths:
    package_root = Path(__file__).resolve().parents[3]
    data_dir = Path(os.getenv("TCM_AGENT_DATA_DIR", str(package_root / "data"))).resolve()
    source_dir = Path(
        os.getenv("TCM_AGENT_SOURCE_DATA_DIR", str(package_root.parent.parent / "DB"))
    ).resolve()
    return DataPaths(data_dir=data_dir, source_dir=source_dir)
