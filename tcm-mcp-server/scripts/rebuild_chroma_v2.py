from __future__ import annotations

import json
import logging
import os
import traceback
from pathlib import Path

from tcm_mcp_server.data.build_chroma import build_vector_store
from tcm_mcp_server.data.database import Database
from tcm_mcp_server.rag.vector_store import VectorStore


def main() -> None:
    stage_dir = Path(
        os.getenv("TCM_AGENT_CHROMA_STAGE", "data/chroma-v2-20260813-c")
    ).resolve()
    stage_dir.mkdir(parents=True, exist_ok=True)
    log_path = stage_dir / "BUILD.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8")],
    )
    db = Database(Path(os.getenv("TCM_AGENT_DB_PATH", "data/tcm.db")).resolve())
    vector_store = VectorStore(stage_dir)
    try:
        db.connect()
        build_vector_store(db, vector_store)
        counts = {
            name: vector_store.count(name)
            for name in ("herbs", "prescriptions", "syndromes", "acupoints")
        }
        (stage_dir / "BUILD_COMPLETE.json").write_text(
            json.dumps({"counts": counts}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        (stage_dir / "BUILD_FAILED.txt").write_text(
            traceback.format_exc(),
            encoding="utf-8",
        )
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
