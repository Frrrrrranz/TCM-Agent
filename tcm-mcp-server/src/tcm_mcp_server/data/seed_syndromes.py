"""
证型种子数据导入脚本。

基于《中医诊断学》十三五规划教材，导入常见证型数据。
"""

from __future__ import annotations

import logging
from pathlib import Path
from .database import Database

logger = logging.getLogger(__name__)

SYNDROMES_DATA = [
    # ── 八纲辨证 ────────────────────────────────────────────
    {
        "name": "太阳中风证",
        "category": "六经辨证",
        "key_symptoms": "头痛，发热，汗出，恶风，脉浮缓",
        "tongue": "苔薄白",
        "pulse": "浮缓",
        "mechanism": "风寒外袭，卫强营弱，营卫不和",
        "treatment_principle": "解肌发表，调和营卫",
        "source": "《中医诊断学》十三五规划教材",
    },
    {
        "name": "太阳伤寒证",
        "category": "六经辨证",
        "key_symptoms": "恶寒，发热，头身疼痛，无汗，气喘，脉浮紧",
        "tongue": "苔薄白",
        "pulse": "浮紧",
        "mechanism": "风寒束表，卫阳被郁，营阴郁滞",
        "treatment_principle": "发汗解表，宣肺平喘",
        "source": "《中医诊断学》十三五规划教材",
    },
    {
        "name": "少阳证",
        "category": "六经辨证",
        "key_symptoms": "往来寒热，胸胁苦满，不欲饮食，心烦喜呕，口苦，咽干，目眩",
        "tongue": "苔薄白或薄黄",
        "pulse": "弦",
        "mechanism": "邪犯少阳，枢机不利，胆火内郁",
        "treatment_principle": "和解少阳",
        "source": "《中医诊断学》十三五规划教材",
    },
    {
        "name": "阳明经证",
        "category": "六经辨证",
        "key_symptoms": "壮热，面赤，烦渴引饮，汗出，脉洪大",
        "tongue": "苔黄燥",
        "pulse": "洪大",
        "mechanism": "邪入阳明，热炽气分，津液耗伤",
        "treatment_principle": "清热生津",
        "source": "《中医诊断学》十三五规划教材",
    },
    {
        "name": "阳明腑实证",
        "category": "六经辨证",
        "key_symptoms": "大便不通，腹痛拒按，潮热，谵语，苔黄燥，脉沉实",
        "tongue": "苔黄厚燥",
        "pulse": "沉实",
        "mechanism": "邪热入里，与肠中糟粕相搏，腑气不通",
        "treatment_principle": "峻下热结",
        "source": "《中医诊断学》十三五规划教材",
    },
    # ── 脏腑辨证 ────────────────────────────────────────────
    {
        "name": "风寒束肺证",
        "category": "脏腑辨证",
        "key_symptoms": "咳嗽，咳痰清稀，恶寒发热，鼻塞流涕，无汗",
        "tongue": "苔薄白",
        "pulse": "浮紧",
        "mechanism": "风寒外袭，肺卫失宣",
        "treatment_principle": "疏风散寒，宣肺止咳",
        "source": "《中医诊断学》十三五规划教材",
    },
    {
        "name": "风热犯肺证",
        "category": "脏腑辨证",
        "key_symptoms": "咳嗽，痰黄黏稠，发热，微恶风寒，咽痛，舌尖红",
        "tongue": "苔薄黄",
        "pulse": "浮数",
        "mechanism": "风热袭肺，肺失清肃",
        "treatment_principle": "疏风清热，宣肺止咳",
        "source": "《中医诊断学》十三五规划教材",
    },
    {
        "name": "脾胃虚寒证",
        "category": "脏腑辨证",
        "key_symptoms": "脘腹疼痛，喜温喜按，呕吐，泄泻，畏寒肢冷",
        "tongue": "舌淡苔白",
        "pulse": "沉迟",
        "mechanism": "脾胃阳虚，运化失职，寒凝气滞",
        "treatment_principle": "温中祛寒，补气健脾",
        "source": "《中医诊断学》十三五规划教材",
    },
    {
        "name": "脾胃气虚证",
        "category": "脏腑辨证",
        "key_symptoms": "面色萎白，气短乏力，食少便溏，语声低微",
        "tongue": "舌淡苔白",
        "pulse": "虚弱",
        "mechanism": "脾胃气虚，运化乏力，气血生化不足",
        "treatment_principle": "益气健脾",
        "source": "《中医诊断学》十三五规划教材",
    },
    {
        "name": "肝气郁结证",
        "category": "脏腑辨证",
        "key_symptoms": "胸胁胀痛，情志抑郁，善太息，月经不调，脉弦",
        "tongue": "苔薄白",
        "pulse": "弦",
        "mechanism": "情志不遂，肝失疏泄，气机郁滞",
        "treatment_principle": "疏肝解郁，理气和中",
        "source": "《中医诊断学》十三五规划教材",
    },
    {
        "name": "心肾阴虚证",
        "category": "脏腑辨证",
        "key_symptoms": "心悸失眠，虚烦神疲，健忘，手足心热，口舌生疮",
        "tongue": "舌红少苔",
        "pulse": "细数",
        "mechanism": "心肾阴虚，虚火内扰，神志不宁",
        "treatment_principle": "滋阴养血，补心安神",
        "source": "《中医诊断学》十三五规划教材",
    },
    {
        "name": "血瘀气滞证",
        "category": "气血津液辨证",
        "key_symptoms": "胸痛如刺，痛有定处，面色晦暗，舌暗有瘀斑",
        "tongue": "舌暗有瘀斑",
        "pulse": "涩",
        "mechanism": "血行不畅，瘀阻脉络，气机阻滞",
        "treatment_principle": "活血化瘀，行气止痛",
        "source": "《中医诊断学》十三五规划教材",
    },
    {
        "name": "湿痰证",
        "category": "气血津液辨证",
        "key_symptoms": "咳嗽痰多，色白易咯，胸膈痞闷，恶心呕吐，肢体困倦",
        "tongue": "苔白滑",
        "pulse": "滑",
        "mechanism": "脾失健运，湿聚成痰，痰阻气机",
        "treatment_principle": "燥湿化痰，理气和中",
        "source": "《中医诊断学》十三五规划教材",
    },
    {
        "name": "风热表证",
        "category": "八纲辨证",
        "key_symptoms": "发热，微恶风寒，头痛，口渴，咳嗽，咽痛，舌尖红",
        "tongue": "舌尖红，苔薄黄",
        "pulse": "浮数",
        "mechanism": "风热外袭，卫表失和，肺失清肃",
        "treatment_principle": "辛凉解表，清热解毒",
        "source": "《中医诊断学》十三五规划教材",
    },
    {
        "name": "气分热盛证",
        "category": "卫气营血辨证",
        "key_symptoms": "壮热，面赤，烦渴，汗出，脉洪大",
        "tongue": "苔黄燥",
        "pulse": "洪大",
        "mechanism": "邪热入气分，热炽津伤",
        "treatment_principle": "清热生津",
        "source": "《中医诊断学》十三五规划教材",
    },
    {
        "name": "三焦火毒证",
        "category": "八纲辨证",
        "key_symptoms": "大热烦躁，口燥咽干，错语不眠，吐血衄血，发斑，下利",
        "tongue": "舌红苔黄",
        "pulse": "数",
        "mechanism": "火热毒邪充斥三焦，气血两燔",
        "treatment_principle": "泻火解毒",
        "source": "《中医诊断学》十三五规划教材",
    },
    {
        "name": "营血虚滞证",
        "category": "气血津液辨证",
        "key_symptoms": "心悸失眠，头晕目眩，面色无华，月经不调，舌淡，脉细",
        "tongue": "舌淡",
        "pulse": "细",
        "mechanism": "营血亏虚，血行滞涩，脏腑失养",
        "treatment_principle": "补血调血",
        "source": "《中医诊断学》十三五规划教材",
    },
    {
        "name": "气郁证",
        "category": "气血津液辨证",
        "key_symptoms": "胸膈痞闷，脘腹胀痛，嗳腐吞酸，恶心呕吐",
        "tongue": "苔薄腻",
        "pulse": "弦",
        "mechanism": "情志不遂，气机郁滞，升降失常",
        "treatment_principle": "行气解郁",
        "source": "《中医诊断学》十三五规划教材",
    },
]


def seed_syndromes(db: Database) -> int:
    """导入证型种子数据。"""
    count = 0
    for data in SYNDROMES_DATA:
        try:
            db.insert_syndrome(data)
            count += 1
        except Exception as exc:
            logger.warning("导入证型 '%s' 失败: %s", data["name"], exc)
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db_path = Path(__file__).resolve().parent.parent.parent / "data" / "tcm.db"
    db = Database(db_path)
    db.connect()
    count = seed_syndromes(db)
    logger.info("证型种子数据导入完成，共 %d 条", count)
