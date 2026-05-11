# -*- coding: utf-8 -*-
"""将训练时的 ImageFolder 类名（带数据集前缀）映射为中文普通水果/作物名。"""
from __future__ import annotations

import re

# Plant Village 缩写前缀 -> 作物（类名其余段为病害/背景等）
_PV_FRUIT: dict[str, str] = {
    "pva": "苹果",
    "pvbb": "蓝莓",
    "pvch": "樱桃",
    "pvgr": "葡萄",
    "pvor": "橙子",
    "pvpe": "桃子",
    "pvra": "树莓",
    "pvst": "草莓",
    "pvto": "番茄",
}

# 英文词根（小写）-> 中文（用于 Fruits-360 等类名首段）
_EN_ZH: dict[str, str] = {
    "apple": "苹果",
    "almond": "杏仁",
    "almonds": "杏仁",
    "apricot": "杏",
    "avocado": "牛油果",
    "banana": "香蕉",
    "bananas": "香蕉",
    "beetroot": "甜菜",
    "blackberry": "黑莓",
    "blueberry": "蓝莓",
    "cabbage": "卷心菜",
    "cantaloupe": "哈密瓜",
    "carambula": "杨桃",
    "carrot": "胡萝卜",
    "cauliflower": "花椰菜",
    "cherry": "樱桃",
    "chestnut": "栗子",
    "clementine": "小柑橘",
    "cocos": "椰子",
    "corn": "玉米",
    "cucumber": "黄瓜",
    "dates": "椰枣",
    "eggplant": "茄子",
    "fig": "无花果",
    "ginger": "姜",
    "gooseberry": "醋栗",
    "granadilla": "百香果",
    "grape": "葡萄",
    "grapes": "葡萄",
    "grapefruit": "柚子",
    "guava": "番石榴",
    "hazelnut": "榛子",
    "huckleberry": "越橘",
    "kaki": "柿子",
    "kiwi": "猕猴桃",
    "kohlrabi": "苤蓝",
    "kumquats": "金桔",
    "lemon": "柠檬",
    "limes": "青柠",
    "lychee": "荔枝",
    "litchi": "荔枝",
    "lichi": "荔枝",
    "mandarine": "橘子",
    "mango": "芒果",
    "mangoes": "芒果",
    "mangostan": "山竹",
    "maracuja": "百香果",
    "melon": "甜瓜",
    "mulberry": "桑葚",
    "nectarine": "油桃",
    "nut": "坚果",
    "onion": "洋葱",
    "orange": "橙子",
    "oranges": "橙子",
    "papaya": "木瓜",
    "papayas": "木瓜",
    "passion": "百香果",
    "peach": "桃子",
    "peanut": "花生",
    "pear": "梨",
    "pears": "梨",
    "pepper": "甜椒",
    "physalis": "灯笼果",
    "pineapple": "菠萝",
    "pistachio": "开心果",
    "pitahaya": "火龙果",
    "plum": "李子",
    "pomegranate": "石榴",
    "potato": "土豆",
    "quince": "榅桲",
    "rambutan": "红毛丹",
    "raspberry": "树莓",
    "redcurrant": "红醋栗",
    "salak": "蛇皮果",
    "strawberry": "草莓",
    "strawberries": "草莓",
    "tamarillo": "树番茄",
    "tangelo": "橘柚",
    "tomato": "番茄",
    "tomatoes": "番茄",
    "walnut": "核桃",
    "watermelon": "西瓜",
    "zucchini": "西葫芦",
    "bean": "豆类",
    "beans": "豆类",
    "hogplum": "李子类",
    "hogpulm": "李子类",
    "jackfruit": "菠萝蜜",
    "soybean": "大豆",
    "soybeans": "大豆",
    "coffee": "咖啡",
    "coconut": "椰子",
    "coconuts": "椰子",
    "pomegranates": "石榴",
    "litchis": "荔枝",
    "guavas": "番石榴",
}


def _first_meaningful_token(rest: str) -> str:
    """从 Fruits-360 风格类名取首段英文词根，如 Apple_Braeburn_1 -> apple, tomato_cherry_red_2 -> tomato."""
    rest = rest.strip("_")
    if not rest:
        return ""
    # 统一小写取首 token
    parts = re.split(r"_+", rest)
    for tok in parts:
        t = tok.lower()
        if not t or t.isdigit():
            continue
        return t
    return ""


def friendly_zh(canonical: str) -> str:
    """
    将 checkpoint 中的类别字符串映射为简短中文名。
    无法识别时返回「其它」。
    """
    s = (canonical or "").strip()
    if not s:
        return "其它"

    # --- Plant Village 水果缩写 ---
    if "__" in s:
        prefix = s.split("__", 1)[0].lower()
        if prefix in _PV_FRUIT:
            return _PV_FRUIT[prefix]

    # --- RawRipe: rawripe__oranges__ripe ---
    if s.startswith("rawripe__"):
        parts = s.split("__")
        if len(parts) >= 2:
            fruit = parts[1].lower().rstrip("s")  # apples -> apple
            return _EN_ZH.get(fruit, _EN_ZH.get(fruit + "s", parts[1]))

    # --- fruit-salad: fruitsalad__apples ---
    if s.startswith("fruitsalad__"):
        tail = s.split("__", 1)[1].lower().rstrip("s")
        return _EN_ZH.get(tail, _EN_ZH.get(tail + "s", s.split("__", 1)[1]))

    # --- locfruits5__apple ---
    if s.startswith("locfruits5__"):
        t = s.split("__", 1)[1].lower()
        return _EN_ZH.get(t, "水果")

    # --- fruitimg_od__mango ---
    if s.startswith("fruitimg_od__"):
        t = _first_meaningful_token(s.split("__", 1)[1])
        return _EN_ZH.get(t, "水果")

    # --- FruitVision（鲜/腐/甲醛）---
    if s.startswith("fruitvision__"):
        if "fresh" in s:
            return "鲜果"
        if "rotten" in s:
            return "变质果"
        if "formalin" in s:
            return "处理样本"
        return "水果"

    # --- Riseholme / 本地 strawberry ---
    if s.startswith("riseholme_sb__") or s.startswith("strawb__"):
        return "草莓"

    # --- banana / chestnut 嵌套 ---
    if s.startswith("banana__"):
        return "香蕉"
    if s.startswith("chestnut__"):
        return "栗子"

    # --- 预处理茄子番茄 ---
    if s.startswith("egg_pre__"):
        return "茄子"
    if s.startswith("tom_pre__"):
        return "番茄"

    # --- ACFR ---
    if s.startswith("acfr__"):
        sub = s.split("__", 1)[1].lower() if "__" in s else ""
        if "almond" in sub:
            return "杏仁"
        if "apple" in sub:
            return "苹果"
        if "mango" in sub:
            return "芒果"

    # --- 单数据集前缀 + 单一类名 ---
    simple_tail = (
        ("pear640__", "梨"),
        ("lemon_ds__", "柠檬"),
        ("cherrybbch81__", "樱桃"),
        ("cherrybbch72__", "樱桃"),
        ("applebbch81__", "苹果"),
        ("appl_mn__", "苹果"),
        ("apple_drone_br__", "苹果"),
        ("embrapa256__", "葡萄"),
        ("wgisd_grape__", "葡萄"),
        ("pistachio__", "开心果"),
    )
    for pref, zh in simple_tail:
        if s.startswith(pref):
            return zh

    # --- Fruits-360 系列：f360orig__ / f360100__ / f3603bp__ ---
    for pref in ("f360orig__", "f360100__", "f3603bp__"):
        if s.startswith(pref):
            rest = s[len(pref) :]
            t = _first_meaningful_token(rest)
            return _EN_ZH.get(t, "水果")

    # --- 兜底：取最后一个 __ 后的首词，或整串首词 ---
    tail = s.split("__")[-1]
    t = _first_meaningful_token(tail)
    if t in _EN_ZH:
        return _EN_ZH[t]
    return "其它"
