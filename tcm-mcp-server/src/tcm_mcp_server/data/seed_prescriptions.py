"""
方剂种子数据导入脚本。

基于《方剂学》十三五规划教材分类，导入经典方剂数据。
"""

from __future__ import annotations

import logging
from pathlib import Path
from .database import Database

logger = logging.getLogger(__name__)

# 方剂种子数据（覆盖 15 类代表方）
PRESCRIPTIONS_DATA = [
    # ── 解表剂 ──────────────────────────────────────────────
    {
        "name": "桂枝汤",
        "source": "《伤寒论》",
        "category": "解表剂",
        "composition": "桂枝9g，白芍9g，炙甘草6g，生姜9g，大枣3枚",
        "effect": "解肌发表，调和营卫",
        "indication": "外感风寒表虚证。头痛发热，汗出恶风，鼻鸣干呕，苔白不渴，脉浮缓或浮弱",
        "syndrome": "太阳中风证",
        "symptoms": "头痛，发热，汗出，恶风，鼻鸣，干呕，脉浮缓",
        "explanation": "方中桂枝解肌发表，散外感风寒为君；白芍益阴敛营，调和营卫为臣；生姜助桂枝散邪，大枣助白芍和营为佐；炙甘草调和诸药为使。",
        "addition": "恶风寒甚者加防风、荆芥；头痛甚者加白芷、川芎",
        "caution": "表实无汗者禁用",
        "source_text": "《方剂学》十三五规划教材",
    },
    {
        "name": "麻黄汤",
        "source": "《伤寒论》",
        "category": "解表剂",
        "composition": "麻黄9g，桂枝6g，杏仁6g，炙甘草3g",
        "effect": "发汗解表，宣肺平喘",
        "indication": "外感风寒表实证。恶寒发热，头身疼痛，无汗而喘，苔薄白，脉浮紧",
        "syndrome": "太阳伤寒证",
        "symptoms": "恶寒，发热，头身疼痛，无汗，气喘，脉浮紧",
        "explanation": "麻黄发汗解表、宣肺平喘为君；桂枝解肌发表、温通经脉为臣；杏仁降利肺气为佐；炙甘草调和诸药为使。",
        "addition": "咳嗽痰多加半夏、陈皮",
        "caution": "表虚自汗者禁用",
        "source_text": "《方剂学》十三五规划教材",
    },
    {
        "name": "银翘散",
        "source": "《温病条辨》",
        "category": "解表剂",
        "composition": "金银花15g，连翘15g，桔梗6g，薄荷6g，竹叶4g，生甘草5g，荆芥穗4g，淡豆豉5g，牛蒡子6g",
        "effect": "辛凉透表，清热解毒",
        "indication": "温病初起。发热无汗，或有汗不畅，微恶风寒，头痛口渴，咳嗽咽痛，舌尖红，苔薄白或薄黄，脉浮数",
        "syndrome": "风热表证",
        "symptoms": "发热，微恶风寒，头痛，口渴，咳嗽，咽痛，舌尖红，脉浮数",
        "explanation": "金银花、连翘清热解毒、疏散风热为君；薄荷、牛蒡子疏散风热、利咽为臣；荆芥穗、淡豆豉助发散为佐；竹叶清热除烦，桔梗宣肺止咳，甘草调和诸药。",
        "addition": "咽痛甚者加板蓝根、玄参",
        "caution": "风寒感冒者不宜使用",
        "source_text": "《方剂学》十三五规划教材",
    },
    # ── 清热剂 ──────────────────────────────────────────────
    {
        "name": "白虎汤",
        "source": "《伤寒论》",
        "category": "清热剂",
        "composition": "石膏50g，知母18g，炙甘草6g，粳米9g",
        "effect": "清热生津",
        "indication": "气分热盛证。壮热面赤，烦渴引饮，汗出恶热，脉洪大有力",
        "syndrome": "阳明气分热盛证",
        "symptoms": "壮热，面赤，烦渴，汗出，脉洪大",
        "explanation": "石膏辛甘大寒、清热泻火为君；知母清热滋阴为臣；粳米、炙甘草益胃护津为佐使。",
        "addition": "热甚者加黄连、黄芩",
        "caution": "表证未解者不宜使用",
        "source_text": "《方剂学》十三五规划教材",
    },
    {
        "name": "黄连解毒汤",
        "source": "《外台秘要》",
        "category": "清热剂",
        "composition": "黄连9g，黄芩6g，黄柏6g，栀子9g",
        "effect": "泻火解毒",
        "indication": "三焦火毒证。大热烦躁，口燥咽干，错语不眠，或热病吐血、衄血，或热甚发斑，身热下利",
        "syndrome": "三焦火毒证",
        "symptoms": "大热烦躁，口燥咽干，错语不眠，吐血衄血，发斑，下利",
        "explanation": "黄连泻心火为君；黄芩泻肺火为臣；黄柏泻肾火，栀子通泻三焦为佐使。",
        "addition": "便秘者加大黄",
        "caution": "脾胃虚寒者忌用",
        "source_text": "《方剂学》十三五规划教材",
    },
    # ── 泻下剂 ──────────────────────────────────────────────
    {
        "name": "大承气汤",
        "source": "《伤寒论》",
        "category": "泻下剂",
        "composition": "大黄12g，厚朴24g，枳实12g，芒硝6g",
        "effect": "峻下热结",
        "indication": "阳明腑实证。大便不通，频转矢气，脘腹痞满，腹痛拒按，按之硬，日晡潮热，神昏谵语",
        "syndrome": "阳明腑实证",
        "symptoms": "大便不通，腹痛拒按，潮热，谵语，苔黄燥，脉沉实",
        "explanation": "大黄泻热通便为君；芒硝软坚润燥为臣；厚朴行气消胀，枳实破气消痞为佐。",
        "addition": "气虚者加人参",
        "caution": "孕妇禁用",
        "source_text": "《方剂学》十三五规划教材",
    },
    # ── 和解剂 ──────────────────────────────────────────────
    {
        "name": "小柴胡汤",
        "source": "《伤寒论》",
        "category": "和解剂",
        "composition": "柴胡24g，黄芩9g，人参9g，半夏9g，炙甘草9g，生姜9g，大枣4枚",
        "effect": "和解少阳",
        "indication": "伤寒少阳证。往来寒热，胸胁苦满，默默不欲饮食，心烦喜呕，口苦，咽干，目眩",
        "syndrome": "少阳证",
        "symptoms": "往来寒热，胸胁苦满，不欲饮食，心烦喜呕，口苦，咽干，目眩",
        "explanation": "柴胡透泄少阳半表之邪为君；黄芩清泄少阳半里之热为臣；人参、大枣益气扶正为佐；半夏、生姜和胃降逆，炙甘草调和诸药。",
        "addition": "口渴甚者去半夏加天花粉",
        "caution": "阴虚血燥者慎用",
        "source_text": "《方剂学》十三五规划教材",
    },
    # ── 温里剂 ──────────────────────────────────────────────
    {
        "name": "理中丸",
        "source": "《伤寒论》",
        "category": "温里剂",
        "composition": "人参9g，干姜9g，炙甘草9g，白术9g",
        "effect": "温中祛寒，补气健脾",
        "indication": "脾胃虚寒证。脘腹疼痛，喜温喜按，呕吐泄泻，不欲饮食，畏寒肢冷",
        "syndrome": "脾胃虚寒证",
        "symptoms": "脘腹疼痛，喜温喜按，呕吐，泄泻，畏寒肢冷，舌淡苔白",
        "explanation": "干姜温中散寒为君；人参补气健脾为臣；白术健脾燥湿为佐；炙甘草益气和中为使。",
        "addition": "寒甚者加附子",
        "caution": "湿热证者忌用",
        "source_text": "《方剂学》十三五规划教材",
    },
    # ── 补益剂 ──────────────────────────────────────────────
    {
        "name": "四君子汤",
        "source": "《太平惠民和剂局方》",
        "category": "补益剂",
        "composition": "人参9g，白术9g，茯苓9g，炙甘草6g",
        "effect": "益气健脾",
        "indication": "脾胃气虚证。面色萎白，语声低微，气短乏力，食少便溏，舌淡苔白，脉虚弱",
        "syndrome": "脾胃气虚证",
        "symptoms": "面色萎白，气短乏力，食少便溏，舌淡苔白，脉虚弱",
        "explanation": "人参益气健脾为君；白术健脾燥湿为臣；茯苓渗湿健脾为佐；炙甘草益气和中为使。",
        "addition": "气虚甚者加黄芪",
        "caution": "阴虚火旺者慎用",
        "source_text": "《方剂学》十三五规划教材",
    },
    {
        "name": "四物汤",
        "source": "《太平惠民和剂局方》",
        "category": "补益剂",
        "composition": "当归10g，川芎8g，白芍12g，熟地黄12g",
        "effect": "补血调血",
        "indication": "营血虚滞证。心悸失眠，头晕目眩，面色无华，月经不调，经少或经闭，舌淡，脉细",
        "syndrome": "营血虚滞证",
        "symptoms": "心悸失眠，头晕目眩，面色无华，月经不调，舌淡，脉细",
        "explanation": "熟地黄滋阴补血为君；当归补血活血为臣；白芍养血敛阴，川芎活血行气为佐。",
        "addition": "血虚甚者加阿胶",
        "caution": "阴虚火旺者慎用",
        "source_text": "《方剂学》十三五规划教材",
    },
    # ── 安神剂 ──────────────────────────────────────────────
    {
        "name": "天王补心丹",
        "source": "《校注妇人良方》",
        "category": "安神剂",
        "composition": "人参15g，茯苓15g，玄参15g，丹参15g，桔梗15g，远志15g，当归30g，五味子30g，麦门冬30g，天门冬30g，柏子仁30g，酸枣仁30g，生地黄120g",
        "effect": "滋阴养血，补心安神",
        "indication": "阴虚血少，神志不安证。心悸失眠，虚烦神疲，梦遗健忘，手足心热，口舌生疮，舌红少苔，脉细数",
        "syndrome": "心肾阴虚证",
        "symptoms": "心悸失眠，虚烦神疲，健忘，手足心热，舌红少苔，脉细数",
        "explanation": "生地黄滋阴养血为君；天冬、麦冬滋阴清热，酸枣仁、柏子仁养心安神为臣；人参补气，五味子敛气，茯苓、远志交通心肾为佐。",
        "addition": "失眠甚者加龙骨、牡蛎",
        "caution": "脾胃虚寒者慎用",
        "source_text": "《方剂学》十三五规划教材",
    },
    # ── 理气剂 ──────────────────────────────────────────────
    {
        "name": "越鞠丸",
        "source": "《丹溪心法》",
        "category": "理气剂",
        "composition": "香附6g，川芎6g，苍术6g，神曲6g，栀子6g",
        "effect": "行气解郁",
        "indication": "六郁证。胸膈痞闷，脘腹胀痛，嗳腐吞酸，恶心呕吐，饮食不消",
        "syndrome": "气郁证",
        "symptoms": "胸膈痞闷，脘腹胀痛，嗳腐吞酸，恶心呕吐",
        "explanation": "香附行气解郁为君；川芎活血祛瘀，苍术燥湿健脾，神曲消食导滞，栀子清热泻火为臣佐。",
        "addition": "气郁甚者加柴胡、郁金",
        "caution": "阴虚火旺者慎用",
        "source_text": "《方剂学》十三五规划教材",
    },
    # ── 活血化瘀剂 ──────────────────────────────────────────
    {
        "name": "血府逐瘀汤",
        "source": "《医林改错》",
        "category": "活血化瘀剂",
        "composition": "桃仁12g，红花9g，当归9g，生地黄9g，牛膝9g，柴胡3g，枳壳6g，赤芍6g，川芎5g，桔梗5g，甘草3g",
        "effect": "活血化瘀，行气止痛",
        "indication": "胸中血瘀证。胸痛头痛，日久不愈，痛如针刺而有定处，或呃逆日久不止，或内热烦闷",
        "syndrome": "血瘀气滞证",
        "symptoms": "胸痛如刺，痛有定处，呃逆，内热烦闷，舌暗有瘀斑",
        "explanation": "桃仁、红花活血化瘀为君；当归、川芎、赤芍助活血为臣；柴胡、枳壳行气，牛膝引血下行，桔梗载药上行为佐。",
        "addition": "瘀痛甚者加乳香、没药",
        "caution": "孕妇禁用",
        "source_text": "《方剂学》十三五规划教材",
    },
    # ── 化痰止咳平喘剂 ──────────────────────────────────────
    {
        "name": "二陈汤",
        "source": "《太平惠民和剂局方》",
        "category": "化痰止咳平喘剂",
        "composition": "半夏15g，橘红15g，茯苓9g，炙甘草5g，生姜7片，乌梅1枚",
        "effect": "燥湿化痰，理气和中",
        "indication": "湿痰证。咳嗽痰多，色白易咯，胸膈痞闷，恶心呕吐，肢体困倦，舌苔白滑，脉滑",
        "syndrome": "湿痰证",
        "symptoms": "咳嗽痰多，色白易咯，胸膈痞闷，恶心呕吐，舌苔白滑，脉滑",
        "explanation": "半夏燥湿化痰为君；橘红理气化痰为臣；茯苓渗湿健脾为佐；炙甘草调和诸药为使。",
        "addition": "寒痰加干姜、细辛",
        "caution": "阴虚燥咳者慎用",
        "source_text": "《方剂学》十三五规划教材",
    },
]


def seed_prescriptions(db: Database) -> int:
    """导入方剂种子数据。"""
    count = 0
    for pres_data in PRESCRIPTIONS_DATA:
        try:
            db.insert_prescription(pres_data)
            count += 1
        except Exception as exc:
            logger.warning("导入方剂 '%s' 失败: %s", pres_data["name"], exc)
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db_path = Path(__file__).resolve().parent.parent.parent / "data" / "tcm.db"
    db = Database(db_path)
    db.connect()
    count = seed_prescriptions(db)
    logger.info("方剂种子数据导入完成，共 %d 条", count)
