"""
穴位种子数据导入脚本。

基于《针灸学》十三五规划教材，导入十四经重要穴位数据。
"""

from __future__ import annotations

import logging
from pathlib import Path
from .database import Database

logger = logging.getLogger(__name__)

ACUPOINTS_DATA = [
    # ── 手太阴肺经 ──────────────────────────────────────────
    {
        "name": "列缺",
        "pinyin": "Lieque",
        "meridian": "手太阴肺经",
        "location": "在前臂桡侧缘，桡骨茎突上方，腕横纹上1.5寸",
        "indication": "咳嗽，气喘，咽喉肿痛，头痛，项强，口眼歪斜，牙痛",
        "operation": "向上斜刺0.3-0.5寸",
        "caution": "",
        "source": "《针灸学》十三五规划教材",
    },
    {
        "name": "尺泽",
        "pinyin": "Chize",
        "meridian": "手太阴肺经",
        "location": "在肘横纹中，肱二头肌腱桡侧凹陷处",
        "indication": "咳嗽，气喘，咳血，潮热，胸部胀满，咽喉肿痛，肘臂挛痛",
        "operation": "直刺0.8-1.2寸",
        "caution": "",
        "source": "《针灸学》十三五规划教材",
    },
    # ── 手阳明大肠经 ────────────────────────────────────────
    {
        "name": "合谷",
        "pinyin": "Hegu",
        "meridian": "手阳明大肠经",
        "location": "在手背，第1、2掌骨间，当第2掌骨桡侧的中点处",
        "indication": "头痛，目赤肿痛，鼻衄，牙痛，口眼歪斜，耳聋，发热，恶寒，无汗，多汗，经闭",
        "operation": "直刺0.5-1寸",
        "caution": "孕妇慎用",
        "source": "《针灸学》十三五规划教材",
    },
    {
        "name": "曲池",
        "pinyin": "Quchi",
        "meridian": "手阳明大肠经",
        "location": "在肘横纹外侧端，屈肘，当尺泽与肱骨外上髁连线中点",
        "indication": "热病，咽喉肿痛，齿痛，目赤痛，头痛，眩晕，上肢不遂，手臂肿痛，腹痛吐泻，高血压",
        "operation": "直刺1-1.5寸",
        "caution": "",
        "source": "《针灸学》十三五规划教材",
    },
    # ── 足阳明胃经 ──────────────────────────────────────────
    {
        "name": "足三里",
        "pinyin": "Zusanli",
        "meridian": "足阳明胃经",
        "location": "在小腿前外侧，当犊鼻下3寸，距胫骨前缘一横指",
        "indication": "胃痛，呕吐，腹胀，泄泻，痢疾，便秘，乳痈，下肢痹痛，水肿，虚劳羸瘦，保健要穴",
        "operation": "直刺1-2寸",
        "caution": "",
        "source": "《针灸学》十三五规划教材",
    },
    {
        "name": "天枢",
        "pinyin": "Tianshu",
        "meridian": "足阳明胃经",
        "location": "在腹中部，脐中旁开2寸",
        "indication": "腹胀肠鸣，绕脐痛，便秘，泄泻，痢疾，月经不调",
        "operation": "直刺1-1.5寸",
        "caution": "",
        "source": "《针灸学》十三五规划教材",
    },
    # ── 足太阴脾经 ──────────────────────────────────────────
    {
        "name": "三阴交",
        "pinyin": "Sanyinjiao",
        "meridian": "足太阴脾经",
        "location": "在小腿内侧，当足内踝尖上3寸，胫骨内侧缘后方",
        "indication": "肠鸣腹胀，泄泻，月经不调，带下，阴挺，不孕，滞产，遗精，阳痿，遗尿，失眠",
        "operation": "直刺1-1.5寸",
        "caution": "孕妇慎用",
        "source": "《针灸学》十三五规划教材",
    },
    {
        "name": "血海",
        "pinyin": "Xuehai",
        "meridian": "足太阴脾经",
        "location": "屈膝，在大腿内侧，髌底内侧端上2寸，当股四头肌内侧头的隆起处",
        "indication": "月经不调，崩漏，经闭，湿疹，瘾疹，丹毒",
        "operation": "直刺1-1.5寸",
        "caution": "",
        "source": "《针灸学》十三五规划教材",
    },
    # ── 手少阴心经 ──────────────────────────────────────────
    {
        "name": "神门",
        "pinyin": "Shenmen",
        "meridian": "手少阴心经",
        "location": "在腕部，腕掌侧横纹尺侧端，尺侧腕屈肌腱的桡侧凹陷处",
        "indication": "心痛，心烦，惊悸，怔忡，失眠，健忘，痴呆，癫狂痫",
        "operation": "直刺0.3-0.5寸",
        "caution": "",
        "source": "《针灸学》十三五规划教材",
    },
    # ── 手太阳小肠经 ────────────────────────────────────────
    {
        "name": "后溪",
        "pinyin": "Houxi",
        "meridian": "手太阳小肠经",
        "location": "在手掌尺侧，微握拳，当小指本节后的远侧掌横纹头赤白肉际",
        "indication": "头项强痛，腰背痛，目赤，耳聋，咽喉肿痛，癫狂痫，疟疾",
        "operation": "直刺0.5-1寸",
        "caution": "",
        "source": "《针灸学》十三五规划教材",
    },
    # ── 足太阳膀胱经 ────────────────────────────────────────
    {
        "name": "委中",
        "pinyin": "Weizhong",
        "meridian": "足太阳膀胱经",
        "location": "在腘横纹中点，当股二头肌腱与半腱肌肌腱的中间",
        "indication": "腰背痛，下肢痿痹，腹痛，急性吐泻，小便不利，遗尿，丹毒",
        "operation": "直刺1-1.5寸",
        "caution": "",
        "source": "《针灸学》十三五规划教材",
    },
    {
        "name": "肾俞",
        "pinyin": "Shenshu",
        "meridian": "足太阳膀胱经",
        "location": "在腰部，当第2腰椎棘突下，旁开1.5寸",
        "indication": "遗精，阳痿，遗尿，月经不调，白带，腰痛，耳鸣，耳聋，水肿",
        "operation": "直刺0.5-1寸",
        "caution": "",
        "source": "《针灸学》十三五规划教材",
    },
    # ── 足少阴肾经 ──────────────────────────────────────────
    {
        "name": "涌泉",
        "pinyin": "Yongquan",
        "meridian": "足少阴肾经",
        "location": "在足底部，卷足时足前部凹陷处，约当足底第2、3趾趾缝纹头端与足跟连线的前1/3与后2/3交点上",
        "indication": "头痛，头晕，咽喉肿痛，失音，便秘，小便不利，小儿惊风，癫狂，昏厥",
        "operation": "直刺0.5-1寸",
        "caution": "",
        "source": "《针灸学》十三五规划教材",
    },
    # ── 手厥阴心包经 ────────────────────────────────────────
    {
        "name": "内关",
        "pinyin": "Neiguan",
        "meridian": "手厥阴心包经",
        "location": "在前臂掌侧，腕横纹上2寸，掌长肌腱与桡侧腕屈肌腱之间",
        "indication": "心痛，心悸，胸闷，胸痛，胃痛，呕吐，呃逆，失眠，癫狂，眩晕",
        "operation": "直刺0.5-1寸",
        "caution": "",
        "source": "《针灸学》十三五规划教材",
    },
    # ── 手少阳三焦经 ────────────────────────────────────────
    {
        "name": "外关",
        "pinyin": "Waiguan",
        "meridian": "手少阳三焦经",
        "location": "在前臂背侧，腕背横纹上2寸，尺骨与桡骨之间",
        "indication": "热病，头痛，目赤肿痛，耳鸣，耳聋，胁肋痛，上肢痹痛",
        "operation": "直刺0.5-1寸",
        "caution": "",
        "source": "《针灸学》十三五规划教材",
    },
    # ── 足少阳胆经 ──────────────────────────────────────────
    {
        "name": "风池",
        "pinyin": "Fengchi",
        "meridian": "足少阳胆经",
        "location": "在项部，当枕骨之下，与风府相平，胸锁乳突肌与斜方肌上端之间的凹陷处",
        "indication": "头痛，眩晕，颈项强痛，目赤痛，目泪出，鼻渊，鼻衄，耳聋，中风，口眼歪斜",
        "operation": "向鼻尖方向斜刺0.8-1.2寸",
        "caution": "",
        "source": "《针灸学》十三五规划教材",
    },
    # ── 足厥阴肝经 ──────────────────────────────────────────
    {
        "name": "太冲",
        "pinyin": "Taichong",
        "meridian": "足厥阴肝经",
        "location": "在足背侧，当第1跖骨间隙的后方凹陷处",
        "indication": "头痛，眩晕，目赤肿痛，口歪，胁痛，遗尿，疝气，崩漏，月经不调，癫痫",
        "operation": "直刺0.5-0.8寸",
        "caution": "",
        "source": "《针灸学》十三五规划教材",
    },
    # ── 任脉 ────────────────────────────────────────────────
    {
        "name": "关元",
        "pinyin": "Guanyuan",
        "meridian": "任脉",
        "location": "在下腹部，前正中线上，当脐中下3寸",
        "indication": "遗尿，小便频数，尿闭，泄泻，腹痛，遗精，阳痿，月经不调，带下，不孕，虚劳羸瘦",
        "operation": "直刺1-1.5寸",
        "caution": "孕妇慎用",
        "source": "《针灸学》十三五规划教材",
    },
    # ── 督脉 ────────────────────────────────────────────────
    {
        "name": "百会",
        "pinyin": "Baihui",
        "meridian": "督脉",
        "location": "在头部，当前发际正中直上5寸，或两耳尖连线的中点处",
        "indication": "头痛，眩晕，中风失语，癫狂，脱肛，泄泻，阴挺，健忘，失眠",
        "operation": "平刺0.5-0.8寸",
        "caution": "",
        "source": "《针灸学》十三五规划教材",
    },
]


def seed_acupoints(db: Database) -> int:
    """导入穴位种子数据。"""
    count = 0
    for data in ACUPOINTS_DATA:
        try:
            db.insert_acupoint(data)
            count += 1
        except Exception as exc:
            logger.warning("导入穴位 '%s' 失败: %s", data["name"], exc)
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db_path = Path(__file__).resolve().parent.parent.parent / "data" / "tcm.db"
    db = Database(db_path)
    db.connect()
    count = seed_acupoints(db)
    logger.info("穴位种子数据导入完成，共 %d 条", count)
