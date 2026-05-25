"""
资源管理器 —— 所有数值变动的唯一入口
每次 add/subtract 均记录到 resource_log，用于前端对账。
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.engine.gamestate import ResourceDelta


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def apply_effects(
    effects: dict[str, int],
    faction_id: str | None = None,
    reason: str = "llm_response",
) -> list[ResourceDelta]:
    """
    将 effects dict 中的数值变更应用到指定势力。

    参数:
        effects: {"treasury": -2000, "stability": 5, ...}
        faction_id: 目标势力 ID，默认使用 player_faction
        reason: 变更原因标识

    返回:
        ResourceDelta 列表（每个变动的审计记录）
    """
    if faction_id is None:
        faction_id = st.session_state.get("player_faction", "")

    if not faction_id:
        return []

    resources = st.session_state.get("resources", {})
    faction_resources = resources.get(faction_id, {})
    if not faction_resources:
        return []

    turn = st.session_state.get("turn_number", 0)
    year = st.session_state.get("year", 0)
    month = st.session_state.get("month", 1)
    deltas: list[ResourceDelta] = []

    for key, delta in effects.items():
        if delta == 0:
            continue
        old_value = faction_resources.get(key, 0)
        new_value = old_value + delta
        # 仅保底不小于 0，不设上限
        new_value = max(0, new_value)
        actual_delta = new_value - old_value

        faction_resources[key] = new_value

        delta_record = ResourceDelta(
            turn=turn,
            year=year,
            month=month,
            faction_id=faction_id,
            resource_key=key,
            delta=actual_delta,
            reason=reason,
            source="llm",
        )
        deltas.append(delta_record)

    # 回写到 session
    st.session_state.resources[faction_id] = faction_resources

    # 写回 Faction 对象
    faction = st.session_state.factions.get(faction_id)
    if faction:
        faction.resources = dict(faction_resources)

    # 记录日志
    log = st.session_state.get("resource_log", [])
    log.extend(deltas)
    st.session_state.resource_log = log

    return deltas


def add_resource(
    faction_id: str,
    key: str,
    amount: int,
    reason: str = "engine",
) -> ResourceDelta | None:
    """单项资源增加。"""
    return _single_change(faction_id, key, abs(amount), reason)


def subtract_resource(
    faction_id: str,
    key: str,
    amount: int,
    reason: str = "engine",
) -> ResourceDelta | None:
    """单项资源减少。"""
    return _single_change(faction_id, key, -abs(amount), reason)


# ---------------------------------------------------------------------------
# 内部
# ---------------------------------------------------------------------------

def _single_change(
    faction_id: str,
    key: str,
    delta: int,
    reason: str,
) -> ResourceDelta | None:
    resources = st.session_state.get("resources", {})
    faction_resources = resources.get(faction_id, {})
    if not faction_resources:
        return None

    old = faction_resources.get(key, 0)
    new = max(0, old + delta)
    faction_resources[key] = new
    st.session_state.resources[faction_id] = faction_resources

    faction = st.session_state.factions.get(faction_id)
    if faction:
        faction.resources = dict(faction_resources)

    record = ResourceDelta(
        turn=st.session_state.get("turn_number", 0),
        year=st.session_state.get("year", 0),
        month=st.session_state.get("month", 1),
        faction_id=faction_id,
        resource_key=key,
        delta=new - old,
        reason=reason,
        source="engine",
    )
    log = st.session_state.get("resource_log", [])
    log.append(record)
    st.session_state.resource_log = log

    return record
