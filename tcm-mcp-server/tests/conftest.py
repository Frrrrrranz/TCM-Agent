from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tcm_mcp_server.data.database import Database
from tcm_mcp_server.data.seed_acupoints import seed_acupoints
from tcm_mcp_server.data.seed_herbs import seed_herbs
from tcm_mcp_server.data.seed_prescriptions import seed_prescriptions
from tcm_mcp_server.data.seed_syndromes import seed_syndromes
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
