"""
ChromaDB 向量库构建脚本。

从 SQLite 数据库中读取中医药数据，构建向量索引。
"""

from __future__ import annotations

import logging
from pathlib import Path

from .database import Database
from ..rag.vector_store import VectorStore
from ..rag.embeddings import EmbeddingManager

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
        "SELECT name, category, nature, taste, meridian, effect, indication FROM herbs"
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
            "name": herb["name"],
            "category": herb["category"],
            "type": "herb",
        })

    if herb_texts:
        vector_store.add_texts("herbs", herb_texts, herb_metadatas)
        logger.info("中药向量索引构建完成，共 %d 条", len(herb_texts))

    # ── 构建方剂向量索引 ──────────────────────────────────────
    logger.info("构建方剂向量索引...")
    prescriptions = db.conn.execute(
        "SELECT name, category, effect, indication, syndrome, symptoms, composition FROM prescriptions"
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
            "name": pres["name"],
            "category": pres["category"],
            "type": "prescription",
        })

    if pres_texts:
        vector_store.add_texts("prescriptions", pres_texts, pres_metadatas)
        logger.info("方剂向量索引构建完成，共 %d 条", len(pres_texts))

    # ── 构建证型向量索引 ──────────────────────────────────────
    logger.info("构建证型向量索引...")
    syndromes = db.conn.execute(
        "SELECT name, category, key_symptoms, tongue, pulse, mechanism, treatment_principle FROM syndromes"
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
            "name": syn["name"],
            "category": syn["category"],
            "key_symptoms": syn["key_symptoms"],
            "type": "syndrome",
        })

    if syn_texts:
        vector_store.add_texts("syndromes", syn_texts, syn_metadatas)
        logger.info("证型向量索引构建完成，共 %d 条", len(syn_texts))

    # ── 构建穴位向量索引 ──────────────────────────────────────
    logger.info("构建穴位向量索引...")
    acupoints = db.conn.execute(
        "SELECT name, meridian, location, indication FROM acupoints"
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
            "name": acu["name"],
            "meridian": acu["meridian"],
            "type": "acupoint",
        })

    if acu_texts:
        vector_store.add_texts("acupoints", acu_texts, acu_metadatas)
        logger.info("穴位向量索引构建完成，共 %d 条", len(acu_texts))

    logger.info("向量库构建完成！")


def main() -> None:
    """主入口：构建向量库。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    db_path = data_dir / "tcm.db"
    chroma_dir = data_dir / "chroma"

    db = Database(db_path)
    db.connect()

    vector_store = VectorStore(chroma_dir)

    build_vector_store(db, vector_store)

    db.close()


if __name__ == "__main__":
    main()
