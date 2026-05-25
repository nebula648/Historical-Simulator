"""
Session 状态管理器
负责 st.session_state 的初始化、重置、快照和持久化。
"""

from __future__ import annotations

import copy
import streamlit as st
from datetime import datetime


# st.session_state 顶层 key 清单及其默认值
_SESSION_DEFAULTS: dict[str, object] = {
    # --- 路由 ---
    "page": "scenario_picker",
    # --- 剧本 ---
    "scenario_id": None,
    "scenario_title": None,
    "scenario_meta": {},
    # --- 游戏状态 ---
    "year": 0,
    "month": 1,
    "season": "春",
    "turn_number": 0,
    "global_flags": {},
    # --- 势力 ---
    "factions": {},
    "player_faction": None,
    # --- 资源 ---
    "resources": {},
    # --- 军事 ---
    "military": {},
    # --- 外交 ---
    "diplomacy": [],
    # --- 版图 ---
    "territory": {},
    # --- 事件 ---
    "scripted_events": [],
    "event_state": "idle",
    "active_event": None,
    "event_queue": [],
    "event_execution_log": [],
    "resolved_events": [],          # 已解决的 mandatory/mandatory_choice 事件 ID 列表（防止死循环）
    # --- 蝴蝶效应 ---
    "butterfly_rules": [],
    "butterfly_flags": {},
    # --- 世界法则（玩家强加的超自然/非历史设定） ---
    "world_rules": [],
    # --- 地图模板（china / europe） ---
    "map_template": "china",
    # --- AI 势力人格 ---
    "ai_personality": {},
    # --- 日志 ---
    "chronicle_log": [],
    "resource_log": [],
    # --- 对账 ---
    "reconciliation_reports": [],
    # --- LLM 调试 ---
    "llm_debug_log": [],
    # --- 天机阁 ---
    "intervention_log": [],
    "last_turn_snapshot": None,     # 上回合执行前的完整状态快照（用于回滚纠错）
    # --- UI 状态 ---
    "sandbox_mode": "strategic",
    "last_command": "",
    "last_turn_result": None,
    # --- 游戏元数据 ---
    "game_started_at": None,
    "debug_mode": False,
    # --- 御前召见 ---
    "active_audience": None,  # dict: {target, chat_history: [{role, content}]} 或 None
}

# 需要纳入快照的 key（用于回滚）
_SNAPSHOT_KEYS = [
    "year", "month", "season", "turn_number", "global_flags",
    "factions", "resources", "military", "diplomacy", "territory",
    "event_state", "active_event", "event_queue", "event_execution_log",
    "chronicle_log", "resource_log",
    "butterfly_flags", "world_rules",
]


def init_session() -> None:
    """初始化所有 st.session_state 顶层 key，仅在首次调用时生效。"""
    for key, default in _SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = _copy_default(default)

    if st.session_state.game_started_at is None:
        st.session_state.game_started_at = datetime.now().isoformat()

    # 初始化地理描述系统
    from src.map.region_data_loader import init_geography_if_needed
    init_geography_if_needed()


def reset_session() -> None:
    """完全重置 session_state（调试用）。"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_session()


def deep_cleanup_for_scenario_switch() -> None:
    """
    剧本切换时的彻底清理 —— 将上一剧本遗留的所有地理描述、区域名称、
    势力边界等缓存全部置空，确保新剧本载入时不会有任何'历史残渣'污染。

    应在 load_scenario() 的最开始调用。
    """
    from src.map.region_data_loader import clear_map_data

    # 1. 清空地理清单缓存
    clear_map_data()

    # 2. 清空所有地图相关 session keys（这些会在新剧本载入时重新填充）
    st.session_state.territory = {}
    st.session_state.factions = {}
    st.session_state.diplomacy = []
    st.session_state.resources = {}
    st.session_state.military = {}
    st.session_state.scripted_events = []
    st.session_state.event_queue = []
    st.session_state.active_event = None
    st.session_state.event_state = "idle"
    st.session_state.butterfly_rules = []
    st.session_state.butterfly_flags = {}
    st.session_state.chronicle_log = []
    st.session_state.resource_log = []
    st.session_state.ai_personality = {}
    st.session_state.last_turn_result = None
    st.session_state.last_turn_snapshot = None
    st.session_state.last_command = ""
    st.session_state.reconciliation_reports = []
    st.session_state.event_execution_log = []
    st.session_state.llm_debug_log = []
    st.session_state.turn_number = 0
    st.session_state.global_flags = {}
    st.session_state.pop("era_power_center_override", None)
    st.session_state.pop("era_intel_org_override", None)
    st.session_state.map_template = "china"
    st.session_state.world_rules = []


# ---------------------------------------------------------------------------
# 快照与回滚 —— AI 逻辑纠错的核心基础设施
# ---------------------------------------------------------------------------

def capture_snapshot() -> None:
    """
    对当前 session_state 中所有 _SNAPSHOT_KEYS 做深拷贝，
    保存为 last_turn_snapshot。
    在每次执行 micro_turn 或 macro_turn 之前调用。
    """
    snapshot: dict[str, object] = {}
    for key in _SNAPSHOT_KEYS:
        value = st.session_state.get(key)
        try:
            snapshot[key] = copy.deepcopy(value)
        except Exception:
            snapshot[key] = value
    st.session_state.last_turn_snapshot = snapshot


def rollback_to_snapshot() -> bool:
    """
    将 session_state 回滚到 last_turn_snapshot 记录的状态。
    撤销上一次推演造成的所有数值、领土、时间变更。

    返回:
        True 表示回滚成功
    """
    snapshot = st.session_state.get("last_turn_snapshot")
    if not snapshot:
        return False

    for key in _SNAPSHOT_KEYS:
        if key in snapshot:
            try:
                st.session_state[key] = copy.deepcopy(snapshot[key])
            except Exception:
                st.session_state[key] = snapshot[key]

    # 清除回滚之后的对账报告（已不适用）
    reports = st.session_state.get("reconciliation_reports", [])
    if reports:
        st.session_state.reconciliation_reports = reports[:-1] if len(reports) > 1 else []

    return True


# ---------------------------------------------------------------------------
# 内部
# ---------------------------------------------------------------------------

def _copy_default(value: object) -> object:
    """对字典/列表默认值执行浅拷贝，避免多次初始化时的引用共享。"""
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, list):
        return list(value)
    return value
