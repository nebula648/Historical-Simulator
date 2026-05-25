"""
区域映射引擎 —— 将自定义 region_id 映射到 Echarts 中国地图标准省份名
"""

from __future__ import annotations

from collections import Counter

# ---------------------------------------------------------------------------
# 自定义 region_id → Echarts china.js 标准省份名（中文）
# 多个自定义区域可以映射到同一个标准省份（Echarts 做省份级着色）
# ---------------------------------------------------------------------------

REGION_TO_ECHARTS: dict[str, str] = {
    # --- 明帝国核心 ---
    "beijing":        "北京",
    "tianjin":        "天津",
    "shanhai_pass":   "河北",
    "baoding":        "河北",
    "zhen_ding":      "河北",
    "xuan_fu":        "河北",
    # --- 明：山西方向 ---
    "tai_yuan":       "山西",
    "da_tong":        "山西",
    # --- 明：山东 ---
    "jinan":          "山东",
    "qing_zhou":      "山东",
    "yan_zhou":       "山东",
    # --- 明：南直隶/江浙 ---
    "nanjing":        "江苏",
    "su_zhou":        "江苏",
    "yang_zhou":      "江苏",
    "feng_yang":      "安徽",
    "an_qing":        "安徽",
    "hang_zhou":      "浙江",
    "ning_bo":        "浙江",
    "jin_hua":        "浙江",
    # --- 明：江西 ---
    "nan_chang":      "江西",
    "gan_zhou":       "江西",
    # --- 明：湖广 ---
    "wu_chang":       "湖北",
    "xiang_yang":     "湖北",
    "jing_zhou":      "湖北",
    "chang_sha":      "湖南",
    # --- 明：福建 ---
    "fu_zhou":        "福建",
    "quan_zhou":      "福建",
    # --- 明：两广 ---
    "guang_zhou":     "广东",
    "zhao_qing":      "广东",
    "gui_lin":        "广西",
    "wu_zhou":        "广西",
    # --- 明：西南 ---
    "gui_yang":       "贵州",
    "yun_nan":        "云南",
    # --- 明：西北 ---
    "han_zhong":      "陕西",
    "xing_yuan":      "陕西",
    "ning_xia":       "宁夏",
    "lan_zhou":       "甘肃",
    "xi_ning":        "青海",
    # --- 明：海南 ---
    "qiong_zhou":     "海南",
    # --- 明：内蒙古边缘 ---
    "ji_ning":        "内蒙古",

    # --- 清帝国 ---
    "sheng_jing":     "辽宁",
    "liao_yang":      "辽宁",
    "tie_ling":       "辽宁",
    "kai_yuan":       "辽宁",
    "ji_lin":         "吉林",
    "ning_gu_ta":     "黑龙江",
    "hei_long_jiang": "黑龙江",
    "horqin":         "内蒙古",
    "khalkha_east":   "内蒙古",
    "chahar":         "内蒙古",

    # --- 大顺 ---
    "xi_an":          "陕西",
    "yan_an":         "陕西",
    "yu_lin":         "陕西",
    "ning_zhou":      "甘肃",
    "ping_liang":     "甘肃",
    "luo_yang":       "河南",
    "kai_feng":       "河南",
    "nan_yang":       "河南",
    "gui_de":         "河南",
    "ping_yang":      "山西",
    "lu_an":          "山西",

    # --- 大西 ---
    "cheng_du":       "四川",
    "chong_qing":     "重庆",
    "kui_zhou":       "重庆",
    "bao_ning":       "四川",
    "shun_qing":      "四川",
    "jia_ding":       "四川",

    # --- 中立 ---
    "mongolia_west":  "内蒙古",
    "turpan":         "新疆",
    "tibet":          "西藏",
    "tai_wan":        "台湾",
}

# 反向映射: Echarts 省份名 → 我们的自定义区域列表
ECHARTS_TO_REGIONS: dict[str, list[str]] = {}
for _rid, _pn in REGION_TO_ECHARTS.items():
    ECHARTS_TO_REGIONS.setdefault(_pn, []).append(_rid)


# ---------------------------------------------------------------------------
# 欧洲地图映射：自定义 region_id → Echarts world.js 标准国家名（英文）
# 多个自定义区域可以映射到同一个现代国家（世界地图做国家级着色）
# ---------------------------------------------------------------------------

EUROPE_REGION_TO_COUNTRY: dict[str, str] = {
    # --- 罗马共和国时代 ---
    "italia":             "Italy",
    "sicilia":            "Italy",
    "sardinia":           "Italy",
    "corsica":            "France",
    "gallia_cisalpina":   "Italy",
    "gallia_narbonensis": "France",
    "gallia_comata":      "France",
    "hispania":           "Spain",
    "lusitania":          "Portugal",
    "britannia":          "United Kingdom",
    "germania":           "Germany",
    "graecia":            "Greece",
    "macedonia":          "Greece",
    "epirus":             "Greece",
    "illyria":            "Croatia",
    "thracia":            "Turkey",
    "asia_minor":         "Turkey",
    "syria":              "Syria",
    "palaestina":         "Israel",
    "aegyptus":           "Egypt",
    "cyrenaica":          "Libya",
    "carthago":           "Tunisia",
    "numidia":            "Algeria",
    "mauretania":         "Morocco",
    "mesopotamia":        "Iraq",
    "armenia":            "Armenia",
    "parthia":            "Iran",
    "dacia":              "Romania",
    "pannonia":           "Hungary",
    "crete":              "Greece",
    "cyprus":             "Cyprus",

    # --- 拿破仑时代 ---
    "france":             "France",
    "britain":            "United Kingdom",
    "austria":            "Austria",
    "prussia":            "Germany",
    "russia":             "Russia",
    "ottoman":            "Turkey",
    "spain":              "Spain",
    "portugal":           "Portugal",
    "netherlands":        "Netherlands",
    "italy_north":        "Italy",
    "naples":             "Italy",
    "sweden":             "Sweden",
    "denmark":            "Denmark",
    "poland":             "Poland",
    "confederation_rhine": "Germany",
    "switzerland":        "Switzerland",
    "sardinia_island":    "Italy",
    "sicily_island":      "Italy",
    "balkans":            "Serbia",
    "hungary":            "Hungary",
    "papal_states":       "Italy",
    "bavaria":            "Germany",
    "saxony":             "Germany",
    "hanover":            "Germany",
}

# 反向映射: 世界地图国家名 → 欧洲自定义区域列表
COUNTRY_TO_EUROPE_REGIONS: dict[str, list[str]] = {}
for _rid, _cn in EUROPE_REGION_TO_COUNTRY.items():
    COUNTRY_TO_EUROPE_REGIONS.setdefault(_cn, []).append(_rid)


# ---------------------------------------------------------------------------
# 以下硬编码字典作为回退（当 geography_manifest.json 不可用时使用）
# 正常游戏流程中，所有地理数据从 st.session_state.current_map_manifest 读取
# ---------------------------------------------------------------------------

_MODERN_TO_MING_FALLBACK: dict[str, str] = {
    "北京":     "京师（北直隶）",
    "天津":     "天津卫（北直隶）",
    "河北":     "北直隶",
    "山西":     "山西布政使司",
    "山东":     "山东布政使司",
    "河南":     "河南布政使司",
    "陕西":     "陕西行都司",
    "甘肃":     "甘肃镇",
    "宁夏":     "宁夏镇",
    "青海":     "朵甘都司",
    "新疆":     "亦力把里",
    "西藏":     "乌斯藏都司",
    "四川":     "四川布政使司",
    "重庆":     "重庆府",
    "湖北":     "湖广布政使司",
    "湖南":     "湖广布政使司",
    "江苏":     "南直隶",
    "安徽":     "南直隶",
    "浙江":     "浙江布政使司",
    "江西":     "江西布政使司",
    "福建":     "福建布政使司",
    "广东":     "广东布政使司",
    "广西":     "广西布政使司",
    "贵州":     "贵州布政使司",
    "云南":     "云南布政使司",
    "辽宁":     "辽东都司",
    "吉林":     "奴儿干都司",
    "黑龙江":   "奴儿干都司",
    "内蒙古":   "漠南蒙古",
    "海南":     "琼州府",
    "台湾":     "东番（琉球）",
}

_PROVINCE_BASE_STATS_FALLBACK: dict[str, dict[str, int]] = {
    "北京":     {"population": 80,  "food": 60, "stability": 55},
    "天津":     {"population": 20,  "food": 30, "stability": 55},
    "河北":     {"population": 300, "food": 70, "stability": 40},
    "山西":     {"population": 400, "food": 50, "stability": 35},
    "山东":     {"population": 500, "food": 75, "stability": 45},
    "河南":     {"population": 450, "food": 65, "stability": 30},
    "陕西":     {"population": 300, "food": 35, "stability": 25},
    "甘肃":     {"population": 60,  "food": 25, "stability": 30},
    "宁夏":     {"population": 25,  "food": 20, "stability": 40},
    "青海":     {"population": 12,  "food": 15, "stability": 50},
    "新疆":     {"population": 35,  "food": 20, "stability": 60},
    "西藏":     {"population": 45,  "food": 15, "stability": 70},
    "四川":     {"population": 180, "food": 60, "stability": 30},
    "重庆":     {"population": 50,  "food": 45, "stability": 35},
    "湖北":     {"population": 350, "food": 80, "stability": 45},
    "湖南":     {"population": 300, "food": 85, "stability": 50},
    "江苏":     {"population": 800, "food": 90, "stability": 55},
    "安徽":     {"population": 400, "food": 75, "stability": 50},
    "浙江":     {"population": 700, "food": 85, "stability": 60},
    "江西":     {"population": 600, "food": 80, "stability": 55},
    "福建":     {"population": 350, "food": 55, "stability": 50},
    "广东":     {"population": 400, "food": 70, "stability": 55},
    "广西":     {"population": 180, "food": 48, "stability": 45},
    "贵州":     {"population": 70,  "food": 30, "stability": 35},
    "云南":     {"population": 140, "food": 42, "stability": 40},
    "辽宁":     {"population": 55,  "food": 28, "stability": 55},
    "吉林":     {"population": 18,  "food": 15, "stability": 70},
    "黑龙江":   {"population": 8,   "food": 10, "stability": 75},
    "内蒙古":   {"population": 45,  "food": 18, "stability": 60},
    "海南":     {"population": 12,  "food": 28, "stability": 45},
    "台湾":     {"population": 5,   "food": 20, "stability": 70},
}


def get_province_stats(
    echarts_name: str,
    owner_faction_id: str,
    factions: dict,
    territory: dict,
    capital_province: str = "",
) -> dict:
    """
    为单个 Echarts 省份生成模拟统计数据。

    参数:
        echarts_name: Echarts 标准省份名（如 '江苏'）
        owner_faction_id: 该省份的控制势力 ID
        factions: 势力字典
        territory: 完整领土映射
        capital_province: 当前国都所在的 Echarts 省份名

    返回:
        {"ming_name": str, "owner_name": str, "owner_color": str,
         "population": int, "food": int, "stability": int,
         "region_count": int, "is_capital": bool}
    """
    import hashlib

    # 从当前时代的地理清单读取数据（带硬回退）
    try:
        from src.map.region_data_loader import (
            get_current_province_name,
            get_current_province_stats,
        )
        ming_name = get_current_province_name(echarts_name)
        base = get_current_province_stats(echarts_name)
    except Exception:
        ming_name = _MODERN_TO_MING_FALLBACK.get(echarts_name, echarts_name)
        base = _PROVINCE_BASE_STATS_FALLBACK.get(
            echarts_name, {"population": 50, "food": 40, "stability": 40}
        )

    faction = factions.get(owner_faction_id) if owner_faction_id != "neutral" else None
    owner_name = faction.name if faction else "无主之地"
    owner_color = faction.color if faction else "#888888"

    # 用省份名哈希生成稳定抖动（±20%）
    seed = int(hashlib.md5(echarts_name.encode()).hexdigest()[:8], 16)
    pop_jitter = 1.0 + ((seed % 40) - 20) / 100.0
    food_jitter = 1.0 + (((seed >> 8) % 40) - 20) / 100.0
    stab_jitter = 1.0 + (((seed >> 16) % 30) - 15) / 100.0

    # 势力因素：腐败度高的势力控制区治安差，稳定度低
    if faction and hasattr(faction, 'resources'):
        corruption = faction.resources.get("corruption", 50)
        stab_penalty = int(corruption * 0.3)
    else:
        stab_penalty = 0

    # 该省份覆盖的自定义区域数（省级 scenario 至少有 1 个区域）
    sub_regions = ECHARTS_TO_REGIONS.get(echarts_name, [])
    region_count = len(sub_regions) if sub_regions else 1

    # 是否为国都所在省份
    is_capital = (echarts_name == capital_province)

    return {
        "ming_name": ming_name,
        "owner_name": owner_name,
        "owner_color": owner_color,
        "population": max(1, int(base["population"] * pop_jitter)),
        "food": max(5, min(100, int(base["food"] * food_jitter))),
        "stability": max(5, min(100, int(base["stability"] * stab_jitter) - stab_penalty)),
        "region_count": region_count,
        "is_capital": is_capital,
    }


def resolve_province_ownership(
    territory: dict[str, str],
    factions: dict,
) -> dict[str, tuple[str, str]]:
    """
    将自定义区域的归属解析为 Echarts 省份归属。

    参数:
        territory: {region_id: faction_id}
        factions: {faction_id: Faction}

    返回:
        {echarts_province_name: (faction_id, faction_color)}
        未归属的省份返回 (None, "#444444")
    """
    province_owners: dict[str, str] = {}

    # 按省份聚合，每个省份取控制区域最多的势力
    for province_name, regions in ECHARTS_TO_REGIONS.items():
        owners = [
            territory.get(r)
            for r in regions
            if territory.get(r) and territory.get(r) != "neutral"
        ]
        # 回退：如果子区域都不存在，尝试将 province_name 本身作为 region_id
        if not owners:
            direct_owner = territory.get(province_name)
            if direct_owner and direct_owner != "neutral":
                owners = [direct_owner]
        if not owners:
            province_owners[province_name] = None
            continue
        # 多数决
        counter = Counter(owners)
        winner = counter.most_common(1)[0][0]
        province_owners[province_name] = winner

    # 构造最终结果
    result: dict[str, tuple[str, str]] = {}
    for province_name, faction_id in province_owners.items():
        if faction_id is None:
            result[province_name] = ("neutral", "#444444")
        else:
            faction = factions.get(faction_id)
            color = faction.color if faction else "#888888"
            result[province_name] = (faction_id, color)

    return result


def build_echarts_map_data(
    territory: dict[str, str],
    factions: dict,
    capital_province: str = "",
) -> list[dict]:
    """
    构造 Echarts map series 所需的 data 数组，附带省份统计数据供 tooltip 使用。
    国都所在省份会获得特殊的金色边框与发光效果。

    返回:
        [{"name": "北京", "value": 1, "itemStyle": {...}, "provinceStats": {...}}, ...]
    """
    province_colors = resolve_province_ownership(territory, factions)
    result: list[dict] = []
    for province_name, (fid, color) in province_colors.items():
        stats = get_province_stats(province_name, fid, factions, territory, capital_province)
        is_capital = stats.get("is_capital", False)

        item_style = {
            "areaColor": color,
            "borderColor": "#FFD700" if is_capital else "#C0B8A8",
            "borderWidth": 3 if is_capital else 1,
            "shadowBlur": 12 if is_capital else 0,
            "shadowColor": "rgba(255, 215, 0, 0.6)" if is_capital else "transparent",
        }

        result.append({
            "name": province_name,
            "value": 1,
            "itemStyle": item_style,
            "label": {"show": False},
            "emphasis": {
                "itemStyle": {
                    "areaColor": color,
                    "shadowBlur": 16 if is_capital else 10,
                    "shadowColor": "rgba(255, 215, 0, 0.8)" if is_capital else "rgba(0,0,0,0.5)",
                    "borderColor": "#FFD700" if is_capital else "#C0B8A8",
                    "borderWidth": 3 if is_capital else 1,
                },
            },
            "provinceStats": stats,
        })
    return result


def get_faction_legend(factions: dict) -> list[dict]:
    """
    构造 Echarts 图例所需的 faction 颜色映射。
    用于在地图下方显示势力图例。
    """
    legend: list[dict] = []
    for fid, faction in factions.items():
        if faction.is_alive:
            legend.append({
                "name": faction.name,
                "color": faction.color,
                "regions": len(faction.controlled_regions),
            })
    return legend


# ---------------------------------------------------------------------------
# 欧洲地图函数
# ---------------------------------------------------------------------------

def resolve_europe_ownership(
    territory: dict[str, str],
    factions: dict,
) -> dict[str, tuple[str, str]]:
    """
    将欧洲自定义区域归属解析为世界地图国家归属。

    返回:
        {country_name: (faction_id, faction_color)}
    """
    country_owners: dict[str, str] = {}

    for country_name, regions in COUNTRY_TO_EUROPE_REGIONS.items():
        owners = [
            territory.get(r)
            for r in regions
            if territory.get(r) and territory.get(r) != "neutral"
        ]
        if not owners:
            direct_owner = territory.get(country_name)
            if direct_owner and direct_owner != "neutral":
                owners = [direct_owner]
        if not owners:
            country_owners[country_name] = None
            continue
        counter = Counter(owners)
        winner = counter.most_common(1)[0][0]
        country_owners[country_name] = winner

    result: dict[str, tuple[str, str]] = {}
    for country_name, faction_id in country_owners.items():
        if faction_id is None:
            result[country_name] = ("neutral", "#444444")
        else:
            faction = factions.get(faction_id)
            color = faction.color if faction else "#888888"
            result[country_name] = (faction_id, color)

    return result


def get_europe_region_stats(
    country_name: str,
    region_id: str,
    owner_faction_id: str,
    factions: dict,
    territory: dict,
    capital_region: str = "",
) -> dict:
    """为单个欧洲区域生成模拟统计数据。"""
    import hashlib

    try:
        from src.map.region_data_loader import (
            get_current_province_name,
            get_current_province_stats,
        )
        display_name = get_current_province_name(region_id)
        base = get_current_province_stats(region_id)
    except Exception:
        display_name = region_id
        base = {"population": 25, "food": 40, "stability": 50}

    faction = factions.get(owner_faction_id) if owner_faction_id != "neutral" else None
    owner_name = faction.name if faction else "无主之地"
    owner_color = faction.color if faction else "#888888"

    seed = int(hashlib.md5(region_id.encode()).hexdigest()[:8], 16)
    pop_jitter = 1.0 + ((seed % 40) - 20) / 100.0
    food_jitter = 1.0 + (((seed >> 8) % 40) - 20) / 100.0
    stab_jitter = 1.0 + (((seed >> 16) % 30) - 15) / 100.0

    if faction and hasattr(faction, 'resources'):
        corruption = faction.resources.get("corruption", 50)
        stab_penalty = int(corruption * 0.3)
    else:
        stab_penalty = 0

    sub_regions = COUNTRY_TO_EUROPE_REGIONS.get(country_name, [])
    region_count = len(sub_regions) if sub_regions else 1

    is_capital = (region_id == capital_region)

    return {
        "ming_name": display_name,
        "owner_name": owner_name,
        "owner_color": owner_color,
        "population": max(1, int(base["population"] * pop_jitter)),
        "food": max(5, min(100, int(base["food"] * food_jitter))),
        "stability": max(5, min(100, int(base["stability"] * stab_jitter) - stab_penalty)),
        "region_count": region_count,
        "is_capital": is_capital,
    }


def build_europe_map_data(
    territory: dict[str, str],
    factions: dict,
    capital_region: str = "",
) -> list[dict]:
    """构造 Echarts world map series 所需的 data 数组（欧洲模式）。"""
    country_colors = resolve_europe_ownership(territory, factions)

    # 确定每个国家的"主区域"用于统计
    country_to_primary_region: dict[str, str] = {}
    for country_name, regions in COUNTRY_TO_EUROPE_REGIONS.items():
        for r in regions:
            if territory.get(r):
                country_to_primary_region[country_name] = r
                break
        if country_name not in country_to_primary_region:
            country_to_primary_region[country_name] = country_name

    result: list[dict] = []
    for country_name, (fid, color) in country_colors.items():
        primary_region = country_to_primary_region.get(country_name, country_name)
        stats = get_europe_region_stats(
            country_name, primary_region, fid, factions, territory, capital_region,
        )
        is_capital = stats.get("is_capital", False)

        item_style = {
            "areaColor": color,
            "borderColor": "#FFD700" if is_capital else "#888888",
            "borderWidth": 3 if is_capital else 1,
            "shadowBlur": 12 if is_capital else 0,
            "shadowColor": "rgba(255, 215, 0, 0.6)" if is_capital else "transparent",
        }

        result.append({
            "name": country_name,
            "value": 1,
            "itemStyle": item_style,
            "label": {"show": False},
            "emphasis": {
                "itemStyle": {
                    "areaColor": color,
                    "shadowBlur": 16 if is_capital else 10,
                    "shadowColor": "rgba(255, 215, 0, 0.8)" if is_capital else "rgba(0,0,0,0.5)",
                    "borderColor": "#FFD700" if is_capital else "#888888",
                    "borderWidth": 3 if is_capital else 1,
                },
            },
            "provinceStats": stats,
        })
    return result
