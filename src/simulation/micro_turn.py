"""
微观推演引擎 —— 玩家指令 -> LLM 推演 -> 状态更新 的完整闭环
支持快照回滚 + 纠错重推 (Snapshot & Regenerate)
"""

from __future__ import annotations

import random
from typing import Any

import streamlit as st

from src.llm.client import generate_response
from src.llm.prompt_builder import build_micro_turn_prompt
from src.llm.json_extractor import extract_json
from src.llm.text_sniffer import sniff_and_merge
from src.engine.resource import apply_effects
from src.engine.reconciliation import reconcile
from src.map.territory_evolver import apply_territory_changes
from src.events.state_machine import tick as event_tick
from src.session.manager import capture_snapshot, rollback_to_snapshot


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def execute_micro_turn(command: str, action_type: str = "public_edict") -> dict[str, Any]:
    """
    执行一个微观推演回合。不推进时间，时间由玩家手动控制。

    参数:
        command: 玩家输入的政令
        action_type: 行动类型 (public_edict / secret_operation)
    """
    # ---- 0. 快照：保存推演前状态 ----
    capture_snapshot()

    # ---- 1. 构造 Prompt ----
    system_prompt, user_prompt = build_micro_turn_prompt(command, action_type)

    return _run_turn(system_prompt, user_prompt, command, "micro")


def regenerate_with_correction(correction_prompt: str) -> dict[str, Any]:
    """
    【天机阁核心】AI 逻辑纠错与重推机制。

    逻辑链条：
      1. 回滚到 last_turn_snapshot（撤销错误回合的所有变更）
      2. 将玩家的 correction_prompt 作为【最高优先级强制约束】注入 Prompt
      3. 重新调用 LLM 生成推演
      4. 走完整对账流程

    参数:
        correction_prompt: 玩家指出的 AI 逻辑谬误（如"北京已陷落，不应出现"）

    返回:
        与 execute_micro_turn 相同格式的结果 dict
    """
    # ---- 1. 回滚到推演前状态 ----
    ok = rollback_to_snapshot()
    if not ok:
        return {
            "ok": False,
            "narrative": "",
            "effects": {},
            "reconciliation": None,
            "used_fallback": False,
            "error": "回滚失败：没有可用的状态快照。请先执行一次正常推演。",
        }

    # ---- 2. 记录纠错日志 ----
    _log_correction(correction_prompt)

    # ---- 3. 重新捕获快照（为可能的再次纠错做准备）----
    capture_snapshot()

    # ---- 4. 构造带强制约束的 Prompt ----
    last_command = st.session_state.get("last_command", "")
    last_action_type = st.session_state.get("last_action_type", "public_edict")
    system_prompt, user_prompt = build_micro_turn_prompt(last_command, last_action_type)

    # 注入强制纠错指令（插入到 User Prompt 最前面，优先级最高）
    forced_user_prompt = (
        f"【🔴 最高优先级纠错指令 —— 必须严格遵守以下事实，不得违背】\n"
        f"{correction_prompt}\n\n"
        f"请基于上述事实修正你的推演逻辑，重新生成本回合的推演结果。"
        f"如果你之前的推演违背了上述事实，必须在本轮纠正。\n\n"
        f"【原始指令】\n{user_prompt}"
    )

    return _run_turn(system_prompt, forced_user_prompt, last_command, "micro_corrected")


def advance_month_and_tick() -> dict[str, Any]:
    """
    推进一个月时间，触发事件轮询。

    这是唯一推进时间的入口。玩家每点击一次"推进一月"，
    时间前进 1 个月。
    """
    month = st.session_state.get("month", 1) + 1
    year = st.session_state.get("year", 0)
    if month > 12:
        month = 1
        year += 1
        if year == 0:
            year = 1

    season_map = {1: "春", 2: "春", 3: "春", 4: "夏", 5: "夏", 6: "夏",
                  7: "秋", 8: "秋", 9: "秋", 10: "冬", 11: "冬", 12: "冬"}

    st.session_state.month = month
    st.session_state.year = year
    st.session_state.season = season_map.get(month, "春")
    st.session_state.turn_number = st.session_state.get("turn_number", 0) + 1

    # 触发事件轮询
    triggered = event_tick()

    # 写入编年史
    season = season_map.get(month, "春")
    if triggered:
        narrative = f"【岁月流转】{season}季，朝堂风云变幻。"
    else:
        idle_narratives = [
            f"【岁月流转】{season}季朝野无事，时光静好。",
            f"【岁月流转】本月风调雨顺，四海升平，各地奏折多为寻常政务。",
            f"【岁月流转】京师米价平稳，商旅往来如常，民间一片安宁景象。",
            f"【岁月流转】内阁照例呈递题本，无非是钱粮刑名之琐事，无甚紧要。",
            f"【岁月流转】是月天朗气清，宫中无事，唯有御花园中桂花初绽。",
            f"【岁月流转】边关塘报依旧，烽火未起；朝中诸臣各司其职，天下粗安。",
        ]
        narrative = random.choice(idle_narratives)

    entry = {
        "year": year,
        "month": month,
        "season": season,
        "text": narrative,
        "category": "system",
        "importance": 0,
    }
    chronicle = st.session_state.get("chronicle_log", [])
    chronicle.append(entry)
    st.session_state.chronicle_log = chronicle

    return {
        "ok": True,
        "narrative": narrative,
        "effects": {},
        "reconciliation": None,
        "used_fallback": False,
        "mode": "advance_month",
        "triggered_event": triggered is not None,
        "error": None,
    }


# ---------------------------------------------------------------------------
# 内部：推演执行核心
# ---------------------------------------------------------------------------

def _run_turn(
    system_prompt: str, user_prompt: str, command: str, mode: str
) -> dict[str, Any]:
    """推演执行核心（micro 和 regenerate 共用）。"""

    # ---- 调用 LLM ----
    try:
        raw_response = generate_response(user_prompt, system_prompt)
    except Exception as e:
        return {
            "ok": False, "narrative": "", "effects": {},
            "reconciliation": None, "used_fallback": False,
            "error": f"LLM 调用失败: {str(e)}",
        }

    _store_debug_info(raw_response, system_prompt, user_prompt)

    # ---- 提取 JSON ----
    parsed = extract_json(raw_response)
    used_fallback = False
    if not parsed or "effects" not in parsed or "narrative" not in parsed:
        parsed = sniff_and_merge(raw_response, parsed)
        used_fallback = True

    narrative = parsed.get("narrative", "天下无事。")
    claimed_effects = parsed.get("effects", {})
    territory_changes = parsed.get("territory_changes", [])
    diplomacy_changes = parsed.get("diplomacy_changes", [])

    # ---- 领土变更 ----
    if territory_changes:
        apply_territory_changes(territory_changes)

    # ---- 外交变更 ----
    if diplomacy_changes:
        _apply_diplomacy_changes(diplomacy_changes)

    # ---- 迁都变更 ----
    capital_change = parsed.get("capital_change")
    if capital_change:
        _apply_capital_change(capital_change, mode)

    # ---- 世界法则变更 ----
    new_world_rules = parsed.get("new_world_rules", [])
    if new_world_rules:
        _apply_world_rules(new_world_rules, mode)

    # ---- 数值变更 ----
    actual_deltas = apply_effects(claimed_effects, reason=f"{mode}_response")

    # ---- 对账 ----
    report = reconcile(claimed_effects, actual_deltas, used_fallback)

    # ---- 编年史 ----
    _append_chronicle(narrative, used_fallback, mode)

    return {
        "ok": True,
        "narrative": narrative,
        "effects": claimed_effects,
        "reconciliation": report,
        "used_fallback": used_fallback,
        "mode": mode,
        "error": None,
    }


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------

def _apply_capital_change(new_capital: str, mode: str) -> None:
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

    # 编年史记录
    tag = "[天机阁纠错重推]" if "corrected" in mode else ""
    entry = {
        "year": st.session_state.get("year", 0),
        "month": st.session_state.get("month", 1),
        "season": st.session_state.get("season", ""),
        "text": f"{tag}【迁都】朝廷移驻 {new_capital}（旧都：{old_capital}）。天子行在自此变更。",
        "category": "system",
        "importance": 3,
    }
    chronicle = st.session_state.get("chronicle_log", [])
    chronicle.append(entry)
    st.session_state.chronicle_log = chronicle


def _apply_world_rules(rules: list[str], mode: str) -> None:
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

    corr_prefix = "[天机阁纠错重推]" if "corrected" in mode else ""
    for rule in added:
        entry = {
            "year": st.session_state.get("year", 0),
            "month": st.session_state.get("month", 1),
            "season": st.session_state.get("season", ""),
            "text": (
                f"{corr_prefix}<span style='color:#9932CC;font-weight:bold;'>"
                f"【🪐 世界法则扭曲】{rule}</span>"
            ),
            "category": "system",
            "importance": 3,
        }
        chronicle = st.session_state.get("chronicle_log", [])
        chronicle.append(entry)
        st.session_state.chronicle_log = chronicle


def _apply_diplomacy_changes(changes: list[dict]) -> None:
    diplomacy = st.session_state.get("diplomacy", [])
    for change in changes:
        a = change.get("a", "")
        b = change.get("b", "")
        tension_delta = change.get("tension_delta", 0)
        new_status = change.get("new_status")
        for rel in diplomacy:
            if (rel.faction_a == a and rel.faction_b == b) or \
               (rel.faction_a == b and rel.faction_b == a):
                rel.tension = max(0, min(100, rel.tension + tension_delta))
                if new_status:
                    rel.status = new_status
                break
    st.session_state.diplomacy = diplomacy


def _append_chronicle(narrative: str, used_fallback: bool, mode: str) -> None:
    prefix = "[嗅探器兜底]" if used_fallback else ""
    corr_prefix = "[天机阁纠错重推]" if "corrected" in mode else ""
    entry = {
        "year": st.session_state.get("year", 0),
        "month": st.session_state.get("month", 1),
        "season": st.session_state.get("season", ""),
        "text": f"{corr_prefix}{prefix} {narrative}",
        "category": "event",
        "importance": 2 if corr_prefix else 1,
    }
    chronicle = st.session_state.get("chronicle_log", [])
    chronicle.append(entry)
    st.session_state.chronicle_log = chronicle


def _advance_time() -> None:
    month = st.session_state.get("month", 1) + 1
    year = st.session_state.get("year", 0)
    if month > 12:
        month = 1
        year += 1
        if year == 0:
            year = 1
    st.session_state.month = month
    st.session_state.year = year
    st.session_state.season = _month_to_season(month)
    st.session_state.turn_number = st.session_state.get("turn_number", 0) + 1
    event_tick()


def _month_to_season(month: int) -> str:
    if 1 <= month <= 3:
        return "春"
    elif 4 <= month <= 6:
        return "夏"
    elif 7 <= month <= 9:
        return "秋"
    else:
        return "冬"


def _store_debug_info(raw_response: str, system_prompt: str, user_prompt: str) -> None:
    debug_log = st.session_state.get("llm_debug_log", [])
    debug_log.append({
        "turn": st.session_state.get("turn_number", 0),
        "system_prompt": system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt,
        "user_prompt": user_prompt[:500] + "..." if len(user_prompt) > 500 else user_prompt,
        "raw_response": raw_response[:1000] + "..." if len(raw_response) > 1000 else raw_response,
    })
    st.session_state.llm_debug_log = debug_log[-10:]


def _log_correction(correction_prompt: str) -> None:
    """记录每次纠错操作。"""
    log = st.session_state.get("intervention_log", [])
    from datetime import datetime
    log.append({
        "time": datetime.now().isoformat(),
        "action": "AI逻辑纠错重推",
        "detail": correction_prompt[:200],
        "turn": st.session_state.get("turn_number", 0),
    })
    st.session_state.intervention_log = log[-50:]
