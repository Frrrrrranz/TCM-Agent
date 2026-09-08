"""
ChromaDB 向量库构建脚本。

从 SQLite 数据库中读取中医药数据，构建向量索引。
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .database import Database
from ..rag.vector_store import VectorStore
from ..rag.embeddings import EmbeddingManager
from .paths import get_data_paths

logger = logging.getLogger(__name__)


def build_vector_store(db: Database, vector_store: VectorStore) -> None:
    """
    从 SQLite 数据库读取数据，构建向量索引。

    为中药、方剂、证型、穴位分别创建集合。
    """
    logger.info("开始构建向量库...")

    # ── 构建中药向量索引 ──────────────────────────────────────
    logger.info("构建中药向量索引...")
    herbs = db.conn.execute(
        "SELECT id, name, category, nature, taste, meridian, effect, indication, "
        "source_file, source_heading, source_text, source_hash, parser_version "
        "FROM herbs"
    ).fetchall()

    herb_texts = []
    herb_metadatas = []
    for herb in herbs:
        text = (
            f"中药名：{herb['name']}。"
            f"分类：{herb['category']}。"
            f"四气：{herb['nature']}。"
            f"五味：{herb['taste']}。"
            f"归经：{herb['meridian']}。"
            f"功效：{herb['effect']}。"
            f"主治：{herb['indication']}。"
        )
        herb_texts.append(text)
        herb_metadatas.append({
            "record_id": str(herb["id"]),
            "name": herb["name"],
            "category": herb["category"],
            "type": "herb",
            "source_file": herb["source_file"],
            "source_heading": herb["source_heading"],
            "source_text": herb["source_text"],
            "source_hash": herb["source_hash"],
            "dataset_version": herb["parser_version"],
        })

    if herb_texts:
        vector_store.add_texts(
            "herbs",
            herb_texts,
            herb_metadatas,
            ids=[f"herb:{herb['id']}" for herb in herbs],
        )
        logger.info("中药向量索引构建完成，共 %d 条", len(herb_texts))

    # ── 构建方剂向量索引 ──────────────────────────────────────
    logger.info("构建方剂向量索引...")
    prescriptions = db.conn.execute(
        "SELECT id, name, category, effect, indication, syndrome, symptoms, composition, "
        "source_file, source_heading, source_text, source_hash, parser_version "
        "FROM prescriptions"
    ).fetchall()

    pres_texts = []
    pres_metadatas = []
    for pres in prescriptions:
        text = (
            f"方剂名：{pres['name']}。"
            f"分类：{pres['category']}。"
            f"功用：{pres['effect']}。"
            f"主治：{pres['indication']}。"
            f"证型：{pres['syndrome']}。"
            f"症状：{pres['symptoms']}。"
            f"组成：{pres['composition']}。"
        )
        pres_texts.append(text)
        pres_metadatas.append({
            "record_id": str(pres["id"]),
            "name": pres["name"],
            "category": pres["category"],
            "type": "prescription",
            "source_file": pres["source_file"],
            "source_heading": pres["source_heading"],
            "source_text": pres["source_text"],
            "source_hash": pres["source_hash"],
            "dataset_version": pres["parser_version"],
        })

    if pres_texts:
        vector_store.add_texts(
            "prescriptions",
            pres_texts,
            pres_metadatas,
            ids=[f"prescription:{pres['id']}" for pres in prescriptions],
        )
        logger.info("方剂向量索引构建完成，共 %d 条", len(pres_texts))

    # ── 构建证型向量索引 ──────────────────────────────────────
    logger.info("构建证型向量索引...")
    syndromes = db.conn.execute(
        "SELECT id, name, category, key_symptoms, tongue, pulse, mechanism, treatment_principle, "
        "source_file, source_heading, source_text, source_hash, parser_version "
        "FROM syndromes"
    ).fetchall()

    syn_texts = []
    syn_metadatas = []
    for syn in syndromes:
        text = (
            f"证型名：{syn['name']}。"
            f"辨证分类：{syn['category']}。"
            f"关键症状：{syn['key_symptoms']}。"
            f"舌象：{syn['tongue']}。"
            f"脉象：{syn['pulse']}。"
            f"病机：{syn['mechanism']}。"
            f"治法：{syn['treatment_principle']}。"
        )
        syn_texts.append(text)
        syn_metadatas.append({
            "record_id": str(syn["id"]),
            "name": syn["name"],
            "category": syn["category"],
            "key_symptoms": syn["key_symptoms"],
            "type": "syndrome",
            "source_file": syn["source_file"],
            "source_heading": syn["source_heading"],
            "source_text": syn["source_text"],
            "source_hash": syn["source_hash"],
            "dataset_version": syn["parser_version"],
        })

    if syn_texts:
        vector_store.add_texts(
            "syndromes",
            syn_texts,
            syn_metadatas,
            ids=[f"syndrome:{syn['id']}" for syn in syndromes],
        )
        logger.info("证型向量索引构建完成，共 %d 条", len(syn_texts))

    # ── 构建穴位向量索引 ──────────────────────────────────────
    logger.info("构建穴位向量索引...")
    acupoints = db.conn.execute(
        "SELECT id, name, meridian, location, indication, source_file, source_heading, "
        "source_text, source_hash, parser_version FROM acupoints"
    ).fetchall()

    acu_texts = []
    acu_metadatas = []
    for acu in acupoints:
        text = (
            f"穴位名：{acu['name']}。"
            f"归经：{acu['meridian']}。"
            f"定位：{acu['location']}。"
            f"主治：{acu['indication']}。"
        )
        acu_texts.append(text)
        acu_metadatas.append({
            "record_id": str(acu["id"]),
            "name": acu["name"],
            "meridian": acu["meridian"],
            "type": "acupoint",
            "source_file": acu["source_file"],
            "source_heading": acu["source_heading"],
            "source_text": acu["source_text"],
            "source_hash": acu["source_hash"],
            "dataset_version": acu["parser_version"],
        })

    if acu_texts:
        vector_store.add_texts(
            "acupoints",
            acu_texts,
            acu_metadatas,
            ids=[f"acupoint:{acu['id']}" for acu in acupoints],
        )
        logger.info("穴位向量索引构建完成，共 %d 条", len(acu_texts))

    logger.info("向量库构建完成！")


def main(argv: list[str] | None = None) -> None:
    """主入口：构建向量库。"""
    parser = argparse.ArgumentParser(description="Build a TCM Chroma index")
    parser.add_argument("--db-path", type=Path)
    parser.add_argument("--chroma-dir", type=Path)
    parser.add_argument("--index-version", default="index-v1")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    paths = get_data_paths()
    db_path = args.db_path or paths.db_path
    chroma_dir = args.chroma_dir or paths.chroma_dir
    if args.chroma_dir is None:
        logger.warning("未指定 --chroma-dir，将使用默认向量库路径: %s", chroma_dir)

    db = Database(db_path)
    db.connect()

    embedding_manager = EmbeddingManager()
    vector_store = VectorStore(
        chroma_dir,
        embedding_manager=embedding_manager,
        index_version=args.index_version,
    )

    build_vector_store(db, vector_store)
    from ..rag.index_manifest import IndexManifest

    collection_names = ("herbs", "prescriptions", "syndromes", "acupoints")
    collection_counts = {
        name: vector_store.count(name) for name in collection_names
    }
    IndexManifest.create(
        index_version=vector_store.index_version,
        embedding_model=embedding_manager.model_name,
        embedding_dimension=embedding_manager.dimension,
        collections=collection_counts,
        dataset_versions=[],
        source_count=sum(collection_counts.values()),
        status="active",
    ).write(vector_store.persist_dir / "index-manifest.json")

    db.close()


if __name__ == "__main__":
    main()
