"""
宏观推演引擎 —— 玩家输入长线国策，LLM 推演 N 年的宏观历史变迁
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.llm.client import generate_response
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

def execute_macro_turn(policy: str, years: int) -> dict[str, Any]:
    """
    执行宏观时间飞跃推演。

    参数:
        policy: 长期大政方针（如"休养生息，编练新军"）
        years: 飞跃年数（1-20）

    返回:
        同 micro_turn 的结果格式
    """
    years = max(1, min(years, 20))

    # ---- 0. 快照：保存推演前状态 ----
    capture_snapshot()

    # ---- 1. 构造 Macro Prompt ----
    system_prompt, user_prompt = _build_macro_prompt(policy, years)

    # ---- 2. 调用 LLM ----
    try:
        raw_response = generate_response(user_prompt, system_prompt)
    except Exception as e:
        return {"ok": False, "narrative": "", "effects": {}, "reconciliation": None, "used_fallback": False, "error": str(e)}

    # ---- 3. 提取 JSON ----
    parsed = extract_json(raw_response)
    used_fallback = False
    if not parsed or "effects" not in parsed or "narrative" not in parsed:
        parsed = sniff_and_merge(raw_response, parsed)
        used_fallback = True

    narrative = parsed.get("narrative", f"经过{years}年的发展，天下形势发生了深刻变化。")
    claimed_effects = parsed.get("effects", {})
    territory_changes = parsed.get("territory_changes", [])

    # ---- 4. 领土变更 ----
    if territory_changes:
        apply_territory_changes(territory_changes)

    # ---- 5. 数值变更 ----
    actual_deltas = apply_effects(claimed_effects, reason="macro_turn")

    # ---- 6. 对账 ----
    report = reconcile(claimed_effects, actual_deltas, used_fallback)

    # ---- 7. 编年史 ----
    _append_macro_chronicle(narrative, years, used_fallback)

    # ---- 8. 推进时间 N 年 ----
    _advance_years(years)

    # ---- 9. 每跃进年触发一次事件轮询 ----
    for _ in range(years):
        triggered = event_tick()
        if triggered:
            # 若触发事件，记录但不在宏指令中打断（由下次微观回合处理）
            break

    return {
        "ok": True,
        "narrative": narrative,
        "effects": claimed_effects,
        "reconciliation": report,
        "used_fallback": used_fallback,
        "years_advanced": years,
        "error": None,
    }


# ---------------------------------------------------------------------------
# Macro Prompt
# ---------------------------------------------------------------------------

MACRO_SYSTEM_PROMPT = """你是一位精通中国历史的严肃历史模拟引擎，正在为「历史模拟器」执行宏观时间飞跃推演。

你的任务：根据玩家给出的长线大政方针和飞跃年数，推演这段时间内的宏大历史变迁。

核心规则：
1. 宏观推演需要概括多年的变化，而非逐月描述。
2. 资源变动的量级应与飞跃年数成正比（5年的变化应是1个月的数十倍）。
3. 考虑连锁反应：一项政策的长期推行会产生远超预期的效果或副作用。
4. 版图可能在多年间发生重大变化：战争胜负、势力兴衰、边境消长。

【输出格式 —— 必须严格遵守】
```json
{
  "narrative": "为你推演的 X 年宏大编年史，用半文言半白话风格，300-500字。应包括：国策执行情况、重大军事外交事件、内部民生变化、天下格局演变。",
  "effects": {
    "treasury": -15000,
    "manpower": 30000,
    "food": 25000,
    "stability": 15,
    "prestige": 10,
    "corruption": 5
  },
  "territory_changes": [],
  "diplomacy_changes": []
}
```

字段要求与微观回合相同。注意数值量级：N 年的变化应该是微观回合的 N×12 倍左右。"""


def _build_macro_prompt(policy: str, years: int) -> tuple[str, str]:
    """构造宏观飞跃 Prompt。"""
    from src.llm.prompt_builder import _serialize_game_state

    state_text = _serialize_game_state(st.session_state)

    user_prompt = f"""【当前游戏状态】
{state_text}

【玩家大政方针】
{policy}

【飞跃年数】
{years} 年

请根据上述状态和国策，推演接下来 {years} 年的宏大历史进程。注意这是长时间跨度的宏观推演，请概括性地描述这个时代的主要变迁。严格按照 JSON 格式输出。"""

    return MACRO_SYSTEM_PROMPT, user_prompt


# ---------------------------------------------------------------------------
# 内部
# ---------------------------------------------------------------------------

def _append_macro_chronicle(narrative: str, years: int, used_fallback: bool) -> None:
    """写入宏观编年史条目。"""
    prefix = "[嗅探器兜底] " if used_fallback else ""
    entry = {
        "year": st.session_state.get("year", 0),
        "month": st.session_state.get("month", 1),
        "season": st.session_state.get("season", ""),
        "text": f"【宏观推演 · {years}年】{prefix}{narrative}",
        "category": "event",
        "importance": 2,
    }
    chronicle = st.session_state.get("chronicle_log", [])
    chronicle.append(entry)
    st.session_state.chronicle_log = chronicle


def regenerate_macro_with_correction(correction_prompt: str) -> dict[str, Any]:
    """
    【天机阁核心】宏观飞跃的 AI 逻辑纠错与重推。

    回滚上次宏观推演 -> 注入强制约束 -> 重新推演。
    """
    ok = rollback_to_snapshot()
    if not ok:
        return {
            "ok": False, "narrative": "", "effects": {},
            "reconciliation": None, "used_fallback": False,
            "error": "回滚失败：没有可用的状态快照。",
        }

    last_command = st.session_state.get("last_command", "")
    # 提取原始国策（格式："[宏指令 X年] 国策内容"）
    policy = last_command.split("] ", 1)[-1] if "] " in last_command else last_command
    years_match = __import__('re').search(r'\[宏指令 (\d+)年\]', last_command)
    years = int(years_match.group(1)) if years_match else 1

    # 重新快照
    capture_snapshot()

    system_prompt, user_prompt = _build_macro_prompt(policy, years)
    forced_user_prompt = (
        f"【🔴 最高优先级纠错指令 —— 必须严格遵守以下事实，不得违背】\n"
        f"{correction_prompt}\n\n"
        f"请基于上述事实修正你的宏观推演，重新生成推演结果。\n\n"
        f"【原始指令】\n{user_prompt}"
    )

    # 复用微观的 _run_turn 逻辑不适合，这里手动执行
    try:
        raw_response = generate_response(forced_user_prompt, system_prompt)
    except Exception as e:
        return {"ok": False, "narrative": "", "effects": {}, "reconciliation": None, "used_fallback": False, "error": str(e)}

    parsed = extract_json(raw_response)
    used_fallback = False
    if not parsed or "effects" not in parsed or "narrative" not in parsed:
        parsed = sniff_and_merge(raw_response, parsed)
        used_fallback = True

    narrative = parsed.get("narrative", "")
    claimed_effects = parsed.get("effects", {})
    territory_changes = parsed.get("territory_changes", [])

    if territory_changes:
        apply_territory_changes(territory_changes)

    actual_deltas = apply_effects(claimed_effects, reason="macro_corrected")
    report = reconcile(claimed_effects, actual_deltas, used_fallback)
    _append_macro_chronicle(narrative, years, used_fallback)
    _advance_years(years)

    return {
        "ok": True, "narrative": narrative, "effects": claimed_effects,
        "reconciliation": report, "used_fallback": used_fallback,
        "years_advanced": years, "mode": "macro_corrected", "error": None,
    }


def _advance_years(years: int) -> None:
    """推进 N 年时间。"""
    year = st.session_state.get("year", 0) + years
    if st.session_state.get("year", 0) < 0 and year >= 0:
        year += 1  # 跳过公元 0 年
    st.session_state.year = year
    st.session_state.turn_number = st.session_state.get("turn_number", 0) + 1
