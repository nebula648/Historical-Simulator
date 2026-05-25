"""
势力数据模型
定义势力、军队、外交关系的核心数据结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# 势力状态
# ---------------------------------------------------------------------------

class FactionStatus(Enum):
    ACTIVE = "active"
    DEFEATED = "defeated"
    VASSALIZED = "vassalized"
    ANNEXED = "annexed"


class GovernmentType(Enum):
    CENTRALIZED_EMPIRE = "中央集权帝国"
    TRIBAL_CONFEDERACY = "部落联盟"
    FEUDAL_KINGDOM = "封建王国"
    VASSAL_STATE = "藩属国"
    REBEL_REGIME = "起义政权"
    WARLORD = "军阀割据"


# ---------------------------------------------------------------------------
# 军队单位
# ---------------------------------------------------------------------------

class UnitType(Enum):
    INFANTRY = "步兵"
    CAVALRY = "骑兵"
    ELITE_INFANTRY = "精锐步兵"
    ELITE_CAVALRY = "精锐骑兵"
    MIXED = "混合部队"
    MILITIA = "民兵"
    NAVY = "水师"
    ARTILLERY = "火器营"


@dataclass
class MilitaryUnit:
    """一支可部署的军事单位。"""
    name: str
    unit_type: str                       # UnitType.value
    size: int                            # 实际兵力数
    location: str                        # 当前驻扎 region_id
    morale: int                          # 0-100
    general: str = ""
    max_size: int = 0                    # 满编兵力（0 表示等同 size）

    def __post_init__(self):
        if self.max_size == 0:
            self.max_size = self.size

    @property
    def strength_ratio(self) -> float:
        """当前兵力占满编的比例。"""
        return self.size / self.max_size if self.max_size > 0 else 0.0

    @property
    def effective_power(self) -> float:
        """有效战斗力 = 兵力 × 士气系数。"""
        return self.size * (self.morale / 100.0)


# ---------------------------------------------------------------------------
# 外交关系
# ---------------------------------------------------------------------------

@dataclass
class DiplomacyRelation:
    """两个势力之间的外交关系。"""
    faction_a: str
    faction_b: str
    status: str       # "war" | "peace" | "alliance" | "vassal" | "tributary" | "neutral"
    tension: int      # 0-100，100 为极度紧张

    def is_hostile(self) -> bool:
        return self.status in ("war",)

    def can_pass_through(self) -> bool:
        """友军是否可以借道。"""
        return self.status in ("alliance", "vassal", "tributary", "peace")


# ---------------------------------------------------------------------------
# 势力
# ---------------------------------------------------------------------------

@dataclass
class Faction:
    """一个势力的完整定义。"""
    faction_id: str
    name: str
    color: str                          # 十六进制颜色 #RRGGBB
    ruler: str
    ruler_title: str                    # 皇帝 / 单于 / 王 / 可汗 等
    government: str                     # GovernmentType.value
    capital: str                        # 首都 region_id
    description: str = ""
    status: str = "active"              # FactionStatus.value
    flag_badass: bool = False           # 是否霸主势力（决定 AI 行为权重）
    faction_type: str = "Empire"        # 势力类型：Empire/Horde/ZombieHorde/Alien/Cult/Rebel/Kingdom/Tribe

    # 运行时属性（从剧本加载后由引擎维护）
    resources: dict[str, int] = field(default_factory=dict)
    military: list[MilitaryUnit] = field(default_factory=list)
    controlled_regions: list[str] = field(default_factory=list)

    # AI 行为参数（从剧本加载）
    aggressiveness: float = 0.5         # 0.0-1.0
    expansionism: float = 0.5           # 0.0-1.0
    diplomacy_preference: str = "neutral"
    decision_weights: dict[str, float] = field(default_factory=dict)

    @property
    def total_manpower(self) -> int:
        """该势力所有军队的总兵力。"""
        return sum(u.size for u in self.military)

    @property
    def average_morale(self) -> float:
        """该势力所有军队的平均士气。"""
        if not self.military:
            return 0.0
        return sum(u.morale for u in self.military) / len(self.military)

    @property
    def is_alive(self) -> bool:
        return self.status == "active"

    def get_resource(self, key: str) -> int:
        return self.resources.get(key, 0)


# ---------------------------------------------------------------------------
# 势力管理器（运行时）
# ---------------------------------------------------------------------------

@dataclass
class FactionManager:
    """管理所有势力的集合及关系。"""
    factions: dict[str, Faction] = field(default_factory=dict)
    relations: list[DiplomacyRelation] = field(default_factory=list)

    def get(self, faction_id: str) -> Faction | None:
        return self.factions.get(faction_id)

    def get_relation(self, a: str, b: str) -> DiplomacyRelation | None:
        for rel in self.relations:
            if (rel.faction_a == a and rel.faction_b == b) or \
               (rel.faction_a == b and rel.faction_b == a):
                return rel
        return None

    def are_at_war(self, a: str, b: str) -> bool:
        rel = self.get_relation(a, b)
        return rel is not None and rel.is_hostile()

    def active_factions(self) -> list[Faction]:
        return [f for f in self.factions.values() if f.is_alive]

    def get_owner(self, region_id: str,
                  territory: dict[str, str]) -> str | None:
        """查询某区域的当前归属势力。"""
        return territory.get(region_id)


# ---------------------------------------------------------------------------
# 动态势力工厂
# ---------------------------------------------------------------------------

# 预生成的颜色池（用于动态势力）
_DYNAMIC_COLOR_POOL = [
    "#4B0082", "#006400", "#8B0000", "#2F4F4F", "#800080",
    "#1E90FF", "#FF4500", "#2E8B57", "#A0522D", "#708090",
    "#DC143C", "#00CED1", "#FFD700", "#8B4513", "#556B2F",
    "#483D8B", "#B8860B", "#008080", "#CD853F", "#4682B4",
]

_INVASION_TITLES = [
    "未知领袖", "舰队司令", "异界之主", "大祭司", "最高指挥官",
    "部落酋长", "星际总督", "混沌领主", "天外来客", "虚空行者",
]

# ---------------------------------------------------------------------------
# 势力类型 → 底层特性映射
# ---------------------------------------------------------------------------

FACTION_TYPE_TRAITS: dict[str, dict] = {
    "Empire": {
        "label": "帝国",
        "description": "传统帝国，需要粮草支撑军队，受腐败度影响",
        "aggressiveness": 0.5,
        "expansionism": 0.5,
        "diplomacy_preference": "neutral",
        "needs_food": True,
        "auto_expand": False,
        "resource_mod": {"treasury": 1.0, "manpower": 1.0, "food": 1.0},
    },
    "Horde": {
        "label": "游牧部族",
        "description": "游牧部族，骑兵为主，高侵略性，不需大量粮草",
        "aggressiveness": 0.8,
        "expansionism": 0.8,
        "diplomacy_preference": "aggressive",
        "needs_food": False,
        "auto_expand": False,
        "resource_mod": {"treasury": 0.5, "manpower": 1.5, "food": 0.3},
    },
    "ZombieHorde": {
        "label": "亡灵天灾",
        "description": "丧尸/亡灵军团，自动向邻接区域扩张，无需外交与粮草，士气恒定",
        "aggressiveness": 1.0,
        "expansionism": 1.0,
        "diplomacy_preference": "none",
        "needs_food": False,
        "auto_expand": True,
        "resource_mod": {"treasury": 0.0, "manpower": 2.0, "food": 0.0},
    },
    "Alien": {
        "label": "异星文明",
        "description": "外星势力，科技碾压，资源体系与传统势力完全不同",
        "aggressiveness": 0.7,
        "expansionism": 0.7,
        "diplomacy_preference": "alien",
        "needs_food": False,
        "auto_expand": False,
        "resource_mod": {"treasury": 2.0, "manpower": 1.5, "food": 0.0},
    },
    "Cult": {
        "label": "修仙宗门/邪教",
        "description": "修仙宗门或邪教组织，以信仰驱动，无视常规军事逻辑",
        "aggressiveness": 0.4,
        "expansionism": 0.6,
        "diplomacy_preference": "isolationist",
        "needs_food": False,
        "auto_expand": False,
        "resource_mod": {"treasury": 0.8, "manpower": 0.5, "food": 0.5},
    },
    "Rebel": {
        "label": "起义军/叛乱",
        "description": "农民起义或地方叛乱，高民心影响，低组织度",
        "aggressiveness": 0.7,
        "expansionism": 0.6,
        "diplomacy_preference": "hostile",
        "needs_food": True,
        "auto_expand": False,
        "resource_mod": {"treasury": 0.3, "manpower": 1.3, "food": 0.6},
    },
    "Kingdom": {
        "label": "封建王国",
        "description": "封建王国，标准军事与外交逻辑",
        "aggressiveness": 0.5,
        "expansionism": 0.5,
        "diplomacy_preference": "neutral",
        "needs_food": True,
        "auto_expand": False,
        "resource_mod": {"treasury": 0.8, "manpower": 0.8, "food": 1.0},
    },
    "Tribe": {
        "label": "部落",
        "description": "原始部落，高士气低装备，易受外交影响",
        "aggressiveness": 0.6,
        "expansionism": 0.4,
        "diplomacy_preference": "defensive",
        "needs_food": False,
        "auto_expand": False,
        "resource_mod": {"treasury": 0.2, "manpower": 1.0, "food": 0.4},
    },
}

# 默认资源（被 faction_type 的 resource_mod 修正）
_AUTO_FACTION_BASE_RESOURCES = {
    "treasury": 50000,
    "manpower": 50000,
    "food": 30000,
    "stability": 70,
    "prestige": 50,
    "corruption": 20,
}


def create_dynamic_faction(
    faction_id: str,
    display_name: str = "",
    faction_type: str = "Empire",
) -> Faction:
    """
    动态创建一个新势力实例。

    参数:
        faction_id: 势力标识符（如 "british_empire"）
        display_name: 显示名称（如 "大英帝国远征舰队"），为空则自动生成
        faction_type: 势力类型（如 "Empire", "ZombieHorde", "Alien" 等）

    返回:
        Faction 实例
    """
    import hashlib

    if not display_name:
        display_name = faction_id.replace("_", " ").title()

    # 用哈希确定性选色
    seed = int(hashlib.md5(faction_id.encode()).hexdigest()[:8], 16)
    color = _DYNAMIC_COLOR_POOL[seed % len(_DYNAMIC_COLOR_POOL)]

    # 根据类型确定统治者头衔
    traits = FACTION_TYPE_TRAITS.get(faction_type, FACTION_TYPE_TRAITS["Empire"])
    if faction_type == "ZombieHorde":
        ruler_title = "尸王"
    elif faction_type == "Alien":
        ruler_title = "远征统帅"
    elif faction_type == "Cult":
        ruler_title = "宗主/教主"
    elif faction_type == "Horde":
        ruler_title = "可汗"
    elif faction_type == "Rebel":
        ruler_title = "首领"
    elif faction_type == "Tribe":
        ruler_title = "酋长"
    elif faction_type == "Kingdom":
        ruler_title = "国王"
    else:
        ruler_title = _INVASION_TITLES[seed % len(_INVASION_TITLES)]

    faction = Faction(
        faction_id=faction_id,
        name=display_name,
        color=color,
        ruler=display_name,
        ruler_title=ruler_title,
        government="未知",
        capital="",
        description=f"【动态势力 · {traits['label']}】由玩家推演中自动生成（ID: {faction_id}）",
        status="active",
        flag_badass=False,
        faction_type=faction_type,
    )

    # 应用类型修正到基础资源
    resource_mod = traits.get("resource_mod", {})
    resources = {}
    for key, base in _AUTO_FACTION_BASE_RESOURCES.items():
        mod = resource_mod.get(key, 1.0)
        resources[key] = int(base * mod)
    faction.resources = resources

    # 应用类型的 AI 行为参数
    faction.aggressiveness = traits.get("aggressiveness", 0.5)
    faction.expansionism = traits.get("expansionism", 0.5)
    faction.diplomacy_preference = traits.get("diplomacy_preference", "neutral")

    faction.controlled_regions = []

    return faction
