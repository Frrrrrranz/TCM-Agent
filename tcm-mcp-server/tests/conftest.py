from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def pytest_configure(config: pytest.Config) -> None:
    # NOTE: pytest 的 --basetemp 只会创建最后一层目录。
    # 若 tmp/pytest 的父目录 tmp/ 不存在，pytest 会直接报 FileNotFoundError (WinError 3)。
    # 在这里提前创建完整路径，确保跨平台（Windows/Linux）开箱即用。
    basetemp = PROJECT_ROOT / "tmp" / "pytest"
    basetemp.mkdir(parents=True, exist_ok=True)
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tcm_mcp_server.data.database import Database
from tcm_mcp_server.data.seed_acupoints import seed_acupoints
from tcm_mcp_server.data.seed_herbs import seed_herbs
from tcm_mcp_server.data.seed_prescriptions import seed_prescriptions
from tcm_mcp_server.data.seed_syndromes import seed_syndromes
from tcm_mcp_server.data.build_chroma import build_vector_store
from tcm_mcp_server.rag.pipeline import RAGPipeline
from tcm_mcp_server.rag.retriever import HybridRetriever
from tcm_mcp_server.rag.vector_store import VectorStore


@pytest.fixture()
def seeded_db(tmp_path: Path) -> Database:
    db = Database(tmp_path / "tcm.db")
    db.connect()
    seed_herbs(db)
    seed_prescriptions(db)
    seed_syndromes(db)
    seed_acupoints(db)
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def pipeline(seeded_db: Database, tmp_path: Path) -> RAGPipeline:
    vector_store = VectorStore(tmp_path / "chroma")
    return RAGPipeline(HybridRetriever(seeded_db, vector_store))


@pytest.fixture(scope="session")
def seeded_vector_pipeline(tmp_path_factory: pytest.TempPathFactory) -> RAGPipeline:
    """带种子数据向量索引的完整 pipeline（用于 RAG 评测）。

    NOTE: 使用 LiteVectorStore（TF-IDF 余弦相似度）替代 ChromaDB，
    规避 ChromaDB 1.5.x Rust 后端在 Windows 上的 access violation 崩溃。
    LiteVectorStore 提供与 VectorStore 相同的 add_texts/similarity_search 接口。
    CI（Linux）环境可切换回 ChromaDB。
    """
    import importlib.util
    _lite_path = Path(__file__).resolve().parent / "rag" / "lite_vector_store.py"
    _spec = importlib.util.spec_from_file_location("lite_vector_store", _lite_path)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    LiteVectorStore = _mod.LiteVectorStore

    tmp_path = tmp_path_factory.mktemp("rag_eval")
    db = Database(tmp_path / "tcm.db")
    db.connect()
    seed_herbs(db)
    seed_prescriptions(db)
    seed_syndromes(db)
    seed_acupoints(db)

    # NOTE: 使用 TF-IDF 轻量级向量存储，避免 ChromaDB Rust 崩溃
    vector_store = LiteVectorStore()
    build_vector_store(db, vector_store)

    pipeline = RAGPipeline(HybridRetriever(db, vector_store))
    yield pipeline
    db.close()

