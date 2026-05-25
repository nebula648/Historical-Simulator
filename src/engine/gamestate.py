"""
游戏状态单一真相源
所有对游戏全局状态的读写都必须经过此模块的数据结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------

class TurnType(Enum):
    MICRO = auto()   # 微观指令回合（1 个月推进）
    MACRO = auto()   # 宏观时间飞跃（N 年推演）


class Season(Enum):
    SPRING = "春"
    SUMMER = "夏"
    AUTUMN = "秋"
    WINTER = "冬"


class EventState(Enum):
    IDLE = "idle"
    TRIGGERED = "triggered"
    AWAITING_CHOICE = "awaiting_choice"
    RESOLVED = "resolved"


class DiplomaticStatus(Enum):
    WAR = "war"
    PEACE = "peace"
    ALLIANCE = "alliance"
    VASSAL = "vassal"
    TRIBUTARY = "tributary"
    NEUTRAL = "neutral"


# ---------------------------------------------------------------------------
# 资源变动日志条目
# ---------------------------------------------------------------------------

@dataclass
class ResourceDelta:
    """单次资源变动的审计记录。用于前端对账。"""
    turn: int
    year: int
    month: int
    faction_id: str
    resource_key: str
    delta: int
    reason: str
    source: str = ""  # "llm" | "engine" | "event" | "manual"


# ---------------------------------------------------------------------------
# 编年史条目
# ---------------------------------------------------------------------------

@dataclass
class ChronicleEntry:
    """编年史中的一条记录。"""
    year: int
    month: int
    season: str
    text: str
    category: str = "general"  # "military" | "diplomacy" | "economy" | "event" | "general"
    importance: int = 0        # 0=普通 1=重要 2=关键节点


# ---------------------------------------------------------------------------
# 领土变更记录
# ---------------------------------------------------------------------------

@dataclass
class TerritoryChange:
    """单次领土变更记录。"""
    region_id: str
    from_faction: str | None   # None 表示此前为无人区
    to_faction: str | None     # None 表示变为无人区
    reason: str
    turn: int


# ---------------------------------------------------------------------------
# 游戏全局状态
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    """游戏全局状态的不可变快照。运行时状态存储在 st.session_state 中。"""
    year: int
    month: int
    season: str
    turn_number: int
    global_flags: dict[str, bool] = field(default_factory=dict)

    @property
    def year_label(self) -> str:
        """返回人类可读的年份标签。"""
        if self.year < 0:
            return f"公元前 {abs(self.year)} 年"
        else:
            return f"公元 {self.year} 年"

    @property
    def date_label(self) -> str:
        """返回带月份的完整日期标签。"""
        return f"{self.year_label} {self.month}月（{self.season}）"

    @staticmethod
    def month_to_season(month: int) -> str:
        if 1 <= month <= 3:
            return "春"
        elif 4 <= month <= 6:
            return "夏"
        elif 7 <= month <= 9:
            return "秋"
        else:
            return "冬"

    def advance_month(self) -> GameState:
        """推进一个月，返回新的 GameState。"""
        new_month = self.month + 1
        new_year = self.year
        if new_month > 12:
            new_month = 1
            new_year = self.year + 1
            # 公元前/公元交界：不存在公元 0 年
            if new_year == 0:
                new_year = 1
        return GameState(
            year=new_year,
            month=new_month,
            season=self.month_to_season(new_month),
            turn_number=self.turn_number + 1,
            global_flags=dict(self.global_flags),
        )

    def advance_years(self, years: int) -> GameState:
        """飞跃 N 年。"""
        new_year = self.year + years
        if self.year < 0 and new_year >= 0:
            new_year += 1  # 跳过公元 0 年
        return GameState(
            year=new_year,
            month=self.month,
            season=self.season,
            turn_number=self.turn_number + 1,
            global_flags=dict(self.global_flags),
        )
