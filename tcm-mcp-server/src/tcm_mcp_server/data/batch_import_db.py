"""批量导入脚本：从 DB/ 目录读取所有 xlsx 文件，解析并写入 SQLite。"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .database import Database
from .import_sqlite import (
    import_herb_record,
    import_prescription_record_batch,
)
from .parse_formula_xlsx import parse_formula_xlsx
from .parse_herb_xlsx import parse_herb_xlsx
from .parse_tcmbank_xlsx import parse_tcmbank_xlsx
from .schema import HerbIngestionRecord, PrescriptionIngestionRecord

logger = logging.getLogger(__name__)

# 数据目录映射：目录名 -> (解析函数, IngestionRecord 类型)
_PARSER_MAP: dict[str, tuple[Any, type]] = {
    "HERB": (parse_herb_xlsx, HerbIngestionRecord),
    "TCMbank": (parse_tcmbank_xlsx, HerbIngestionRecord),
    "TCM-Formula": (parse_formula_xlsx, PrescriptionIngestionRecord),
}

# 每个数据目录对应的 source 标签（用于生成 review JSON 时的标识）
_SOURCE_LABEL: dict[str, str] = {
    "HERB": "HERB",
    "TCMbank": "TCMbank",
    "TCM-Formula": "TCM-Formula",
}


def scan_xlsx_files(db_dir: str | Path) -> list[dict[str, Any]]:
    """扫描 DB/ 下各子目录，返回待处理文件清单。

    返回格式：
    [
        {
            "dir": "HERB",
            "file": Path("DB/HERB/HERB/xxx.xlsx"),
            "parser": parse_herb_xlsx,
            "record_type": HerbIngestionRecord,
            "source": "HERB",
        },
        ...
    ]
    """
    db_path = Path(db_dir)
    tasks: list[dict[str, Any]] = []

    for subdir, (parser_fn, record_type) in _PARSER_MAP.items():
        target_dir = db_path / subdir / subdir  # e.g. DB/HERB/HERB/
        source_label = _SOURCE_LABEL.get(subdir, subdir)

        if not target_dir.is_dir():
            logger.warning("目录不存在，跳过: %s", target_dir)
            continue

        xlsx_files = sorted(target_dir.glob("*.xlsx"))
        for f in xlsx_files:
            tasks.append({
                "dir": subdir,
                "file": str(f.resolve()),
                "parser": parser_fn,
                "record_type": record_type,
                "source": source_label,
            })

    return tasks


def run_batch_import(
    db_path: str | Path,
    db_dir: str | Path,
    review_dir: str | Path,
    summary_path: str | Path | None = None,
) -> dict[str, Any]:
    """执行批量导入全流程。

    Args:
        db_path: SQLite 数据库文件路径。
        db_dir: DB/ 数据目录路径。
        review_dir: 待人工审核的 JSON 输出目录。
        summary_path: 汇总报告 JSON 路径（可选）。

    Returns:
        汇总统计字典。
    """
    review_path = Path(review_dir)
    review_path.mkdir(parents=True, exist_ok=True)

    db = Database(db_path)
    db.connect()

    tasks = scan_xlsx_files(db_dir)
    logger.info("共发现 %d 个 xlsx 文件待处理", len(tasks))

    # ── 分文件解析与入库 ──────────────────────────────────────
    file_results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for task in tasks:
        logger.info("处理: %s [%s]", task["file"], task["dir"])
        try:
            records = task["parser"](task["file"])
        except Exception as exc:
            logger.error("解析失败: %s — %s", task["file"], exc)
            errors.append({"file": task["file"], "phase": "parse", "error": str(exc)})
            continue

        if task["record_type"] is PrescriptionIngestionRecord:
            # ── 方剂批量导入 ──────────────────────────────────
            counts = import_prescription_record_batch(db, records, review_path)
            file_results.append({
                "file": task["file"],
                "dir": task["dir"],
                "total": len(records),
                "imported": counts["imported"],
                "skipped": counts["skipped"],
                "reviewed": counts["reviewed"],
                "errors": counts["errors"],
                "review_reason": None,
            })

        elif task["record_type"] is HerbIngestionRecord:
            # ── 草药逐条导入（含验证） ─────────────────────────
            herb_counts = {"imported": 0, "reviewed": 0, "errors": 0}
            for record in records:
                try:
                    ok = import_herb_record(db, record, review_path)
                    if ok:
                        herb_counts["imported"] += 1
                    else:
                        herb_counts["reviewed"] += 1
                except Exception as exc:
                    herb_counts["errors"] += 1
                    logger.error("导入草药记录异常: %s — %s", record.name, exc)

            file_results.append({
                "file": task["file"],
                "dir": task["dir"],
                "total": len(records),
                "imported": herb_counts["imported"],
                "skipped": 0,
                "reviewed": herb_counts["reviewed"],
                "errors": herb_counts["errors"],
                "review_reason": None,
            })

    db.close()

    # ── 汇总统计 ─────────────────────────────────────────────
    total_records = sum(r["total"] for r in file_results)
    total_imported = sum(r["imported"] for r in file_results)
    total_skipped = sum(r["skipped"] for r in file_results)
    total_reviewed = sum(r["reviewed"] for r in file_results)
    total_errors = sum(r["errors"] for r in file_results) + len(errors)

    # 按数据目录汇总
    dir_summary: dict[str, dict[str, int]] = {}
    for r in file_results:
        d = r["dir"]
        if d not in dir_summary:
            dir_summary[d] = {"files": 0, "records": 0, "imported": 0, "reviewed": 0, "errors": 0}
        dir_summary[d]["files"] += 1
        dir_summary[d]["records"] += r["total"]
        dir_summary[d]["imported"] += r["imported"]
        dir_summary[d]["reviewed"] += r["reviewed"]
        dir_summary[d]["errors"] += r["errors"]

    summary: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "db_path": str(db_path),
        "review_dir": str(review_path),
        "files_found": len(tasks),
        "total_records": total_records,
        "total_imported": total_imported,
        "total_skipped": total_skipped,
        "total_reviewed": total_reviewed,
        "total_errors": total_errors,
        "dir_summary": dir_summary,
        "file_results": file_results,
    }

    if errors:
        summary["parse_errors"] = errors

    # 写入汇总报告
    if summary_path:
        summary_file = Path(summary_path)
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        summary_file.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        logger.info("汇总报告已写入: %s", summary_file)

    logger.info(
        "批量导入完成: %d 文件, %d 条记录, 已导入 %d, 跳过 %d, 待审核 %d, 错误 %d",
        len(tasks),
        total_records,
        total_imported,
        total_skipped,
        total_reviewed,
        total_errors,
    )

    return summary


def main() -> None:
    """CLI 入口。"""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 默认路径基于脚本位置推导
    default_data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    default_db_dir = default_data_dir.parent.parent.parent.parent / "DB"  # TCM-Agent/../../
    default_db = default_data_dir / "tcm.db"
    default_review = default_data_dir / "review_queue"
    default_summary = default_data_dir / "batch_import_summary.json"

    parser = argparse.ArgumentParser(description="批量导入 DB/ 数据到 SQLite")
    parser.add_argument("--db-path", default=str(default_db), help="SQLite 数据库路径")
    parser.add_argument("--db-dir", default=str(default_db_dir), help="DB/ 数据目录路径")
    parser.add_argument("--review-dir", default=str(default_review), help="待审核输出目录")
    parser.add_argument("--summary", default=str(default_summary), help="汇总报告 JSON 路径")
    parser.add_argument("--no-summary", action="store_true", help="不输出汇总报告文件")

    args = parser.parse_args()

    summary_path = None if args.no_summary else args.summary

    start = time.time()
    run_batch_import(
        db_path=args.db_path,
        db_dir=args.db_dir,
        review_dir=args.review_dir,
        summary_path=summary_path,
    )
    elapsed = time.time() - start
    logger.info("总耗时: %.2f 秒", elapsed)


if __name__ == "__main__":
    main()