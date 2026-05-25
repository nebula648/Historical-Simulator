"""
后果执行器 —— 解析事件选项中的 effects / territory_changes / diplomacy_changes
并精准调用 engine 层进行数值和版图变更。
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.engine.resource import apply_effects
from src.map.territory_evolver import apply_territory_changes


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def execute_consequence(event: dict, choice: dict) -> None:
    """
    执行玩家选中选项的后果。

    处理顺序：
      1. effects → engine.resource.apply_effects
      2. territory_changes → territory_evolver.apply_territory_changes
      3. diplomacy_changes → 更新外交关系
      4. trigger_event → 连锁触发后续事件
      5. 写入编年史

    参数:
        event: 完整事件 dict
        choice: 玩家选中的选项 dict
    """
    player_faction = st.session_state.get("player_faction", "")
    event_title = event.get("title", "事件")
    narrative_result = choice.get("narrative_result", "")

    # ---- 1. 数值变更 ----
    effects = choice.get("effects", {})
    if effects:
        apply_effects(effects, faction_id=player_faction, reason=f"event:{event.get('id')}:{choice.get('id')}")

    # ---- 2. 领土变更 ----
    territory_changes = choice.get("territory_changes", [])
    if territory_changes:
        apply_territory_changes(territory_changes)

    # ---- 3. 外交变更 ----
    diplomacy_changes = choice.get("diplomacy_changes", [])
    if diplomacy_changes:
        _apply_diplomacy(diplomacy_changes)

    # ---- 4. 连锁事件 ----
    trigger_next = effects.get("trigger_event") if isinstance(effects, dict) else None
    if trigger_next:
        from src.events.state_machine import trigger_event_by_id
        trigger_event_by_id(trigger_next)

    # ---- 5. 编年史 ----
    entry = {
        "year": st.session_state.get("year", 0),
        "month": st.session_state.get("month", 1),
        "season": st.session_state.get("season", ""),
        "text": f"【{event_title}】{narrative_result}",
        "category": "event",
        "importance": 2,
    }
    chronicle = st.session_state.get("chronicle_log", [])
    chronicle.append(entry)
    st.session_state.chronicle_log = chronicle


def execute_crisis_resolution(event: dict, player_decision: str) -> dict:
    """
    LLM 驱动的自由意志危机裁决引擎。

    将玩家的自由文本决策发给 LLM，由 LLM 动态生成后果（effects、
    territory_changes、diplomacy_changes），并应用到游戏状态。

    参数:
        event: 完整事件 dict
        player_decision: 玩家自由输入的决策文本

    返回:
        裁决结果 dict，包含 narrative / effects / reconciliation 等字段
    """
    from src.llm.client import generate_response
    from src.llm.prompt_builder import build_crisis_resolution_prompt
    from src.llm.json_extractor import extract_json
    from src.llm.text_sniffer import sniff_and_merge
    from src.engine.reconciliation import reconcile

    event_title = event.get("title", "事件")
    player_faction = st.session_state.get("player_faction", "")

    system_prompt, user_prompt = build_crisis_resolution_prompt(event, player_decision)

    try:
        raw_response = generate_response(user_prompt, system_prompt)
    except Exception as e:
        return {
            "ok": False,
            "narrative": "朝堂上一片哗然。皇帝的决定引发了激烈争论，但因局势混乱，实际效果甚微。",
            "error": str(e),
        }

    parsed = extract_json(raw_response)
    if not parsed or "effects" not in parsed or "narrative" not in parsed:
        parsed = sniff_and_merge(raw_response, parsed)

    narrative_result = parsed.get("narrative", "朝堂上下议论纷纷，此事暂且搁置。")
    claimed_effects = parsed.get("effects", {})
    territory_changes = parsed.get("territory_changes", [])
    diplomacy_changes = parsed.get("diplomacy_changes", [])

    if territory_changes:
        apply_territory_changes(territory_changes)

    if diplomacy_changes:
        _apply_diplomacy(diplomacy_changes)

    # ---- 迁都变更 ----
    capital_change = parsed.get("capital_change")
    if capital_change:
        _apply_capital_change(capital_change, event_title)

    # ---- 世界法则变更 ----
    new_world_rules = parsed.get("new_world_rules", [])
    if new_world_rules:
        _apply_world_rules(new_world_rules)

    actual_deltas = apply_effects(claimed_effects, faction_id=player_faction, reason=f"crisis:{event.get('id')}")

    report = reconcile(claimed_effects, actual_deltas, False)

    entry = {
        "year": st.session_state.get("year", 0),
        "month": st.session_state.get("month", 1),
        "season": st.session_state.get("season", ""),
        "text": f"【{event_title}】{narrative_result}",
        "category": "event",
        "importance": 2,
    }
    chronicle = st.session_state.get("chronicle_log", [])
    chronicle.append(entry)
    st.session_state.chronicle_log = chronicle

    return {
        "ok": True,
        "narrative": narrative_result,
        "effects": claimed_effects,
        "reconciliation": report,
    }


def execute_auto_effects(event: dict) -> None:
    """
    执行 outcome 类型事件的 auto_effects（无需玩家选择）。
    会同时应用 effects、territory_changes、diplomacy_changes。
    """
    # 势力级 auto_effects: {"ming_empire": {"treasury": -3000}, "qing_empire": {...}}
    auto_effects = event.get("auto_effects", {})
    for faction_id, effects in auto_effects.items():
        if isinstance(effects, dict) and effects:
            apply_effects(effects, faction_id=faction_id, reason=f"event_auto:{event.get('id')}")

    # 全局 territory_changes
    territory_changes = event.get("territory_changes", [])
    if territory_changes:
        apply_territory_changes(territory_changes)

    # 全局 diplomacy_changes
    diplomacy_changes = event.get("diplomacy_changes", [])
    if diplomacy_changes:
        _apply_diplomacy(diplomacy_changes)


# ---------------------------------------------------------------------------
# 内部
# ---------------------------------------------------------------------------

def _apply_capital_change(new_capital: str, event_title: str) -> None:
    """强制更新大明国都。"""
    player_faction = st.session_state.get("player_faction", "")
    factions = st.session_state.get("factions", {})
    faction = factions.get(player_faction)
    if not faction:
        return

    old_capital = getattr(faction, 'capital', 'beijing')
    if old_capital == new_capital:
        return

    faction.capital = new_capital
    st.session_state.factions[player_faction] = faction

    entry = {
        "year": st.session_state.get("year", 0),
        "month": st.session_state.get("month", 1),
        "season": st.session_state.get("season", ""),
        "text": f"【{event_title}】迁都：朝廷移驻 {new_capital}（旧都：{old_capital}）。天子行在自此变更。",
        "category": "system",
        "importance": 3,
    }
    chronicle = st.session_state.get("chronicle_log", [])
    chronicle.append(entry)
    st.session_state.chronicle_log = chronicle


def _apply_world_rules(rules: list[str]) -> None:
    """将新增的世界法则持久化到 session_state。"""
    existing = st.session_state.get("world_rules", [])
    added: list[str] = []
    for rule in rules:
        if rule not in existing:
            existing.append(rule)
            added.append(rule)

    if not added:
        return

    st.session_state.world_rules = existing

    for rule in added:
        entry = {
            "year": st.session_state.get("year", 0),
            "month": st.session_state.get("month", 1),
            "season": st.session_state.get("season", ""),
            "text": (
                f"<span style='color:#9932CC;font-weight:bold;'>"
                f"【🪐 世界法则扭曲】{rule}</span>"
            ),
            "category": "system",
            "importance": 3,
        }
        chronicle = st.session_state.get("chronicle_log", [])
        chronicle.append(entry)
        st.session_state.chronicle_log = chronicle


def _apply_diplomacy(changes: list[dict]) -> None:
    """应用外交关系变更。"""
    diplomacy = st.session_state.get("diplomacy", [])

    for change in changes:
        a = change.get("a", "")
        b = change.get("b", "")
        tension_delta = change.get("tension_delta", 0)
        new_status = change.get("new_status")

        # 查找已有关系
        found = False
        for rel in diplomacy:
            rel_a = rel.faction_a if hasattr(rel, 'faction_a') else rel.get('faction_a', '')
            rel_b = rel.faction_b if hasattr(rel, 'faction_b') else rel.get('faction_b', '')
            if (rel_a == a and rel_b == b) or (rel_a == b and rel_b == a):
                current_tension = rel.tension if hasattr(rel, 'tension') else rel.get('tension', 0)
                new_tension = max(0, min(100, current_tension + tension_delta))
                if hasattr(rel, 'tension'):
                    rel.tension = new_tension
                else:
                    rel['tension'] = new_tension
                if new_status:
                    if hasattr(rel, 'status'):
                        rel.status = new_status
                    else:
                        rel['status'] = new_status
                found = True
                break

        # 新建关系
        if not found:
            from src.engine.faction import DiplomacyRelation
            diplomacy.append(DiplomacyRelation(
                faction_a=a,
                faction_b=b,
                status=new_status or "neutral",
                tension=max(0, min(100, 50 + tension_delta)),
            ))

    st.session_state.diplomacy = diplomacy

    # 写入编年史
    for change in changes:
        a = change.get("a", "")
        b = change.get("b", "")
        new_status = change.get("new_status", "")
        if new_status:
            factions = st.session_state.get("factions", {})
            name_a = factions[a].name if a in factions else a
            name_b = factions[b].name if b in factions else b
            entry = {
                "year": st.session_state.get("year", 0),
                "month": st.session_state.get("month", 1),
                "season": st.session_state.get("season", ""),
                "text": f"【外交变更】{name_a} 与 {name_b} 的关系变为：{new_status}",
                "category": "diplomacy",
                "importance": 1,
            }
            chronicle = st.session_state.get("chronicle_log", [])
            chronicle.append(entry)
            st.session_state.chronicle_log = chronicle
