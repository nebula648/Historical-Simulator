"""
事件状态机 —— 管理事件生命周期
状态：idle → triggered → awaiting_choice → resolved → idle
"""

from __future__ import annotations

from typing import Any

import streamlit as st


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def tick() -> dict | None:
    """
    每回合调用一次的事件轮询。

    逻辑：
      1. 若当前有待处理事件 (awaiting_choice)，不触发新事件
      2. 检查事件队列中是否有待执行的 follow_up 事件
      3. 轮询 scripted_events，找到第一个满足条件的触发

    返回:
        触发的事件 dict，或 None
    """
    # 如果玩家正在做选择，不打断
    if st.session_state.get("event_state") == "awaiting_choice":
        return None

    # 检查事件队列（处理 follow_up 事件）
    event_queue: list = st.session_state.get("event_queue", [])
    if event_queue:
        next_event = event_queue.pop(0)
        st.session_state.event_queue = event_queue
        _trigger_event(next_event)
        return next_event

    # 轮询剧本事件
    from src.events.condition import poll_events
    triggered = poll_events()

    if triggered:
        _trigger_event(triggered)
        return triggered

    return None


def trigger_event_by_id(event_id: str) -> bool:
    """手动触发指定 ID 的事件（用于 choice 的 trigger_event 效果）。"""
    # 已解决的事件不再重复触发
    resolved = st.session_state.get("resolved_events", [])
    if event_id in resolved:
        return False

    events = st.session_state.get("scripted_events", [])
    for evt in events:
        if evt.get("id") == event_id:
            # 加入队列而不是立即触发
            queue = st.session_state.get("event_queue", [])
            queue.append(evt)
            st.session_state.event_queue = queue
            return True
    return False


def resolve_event_with_decision(player_decision: str) -> bool:
    """
    玩家自由输入决策后调用。将玩家的自由文本发给 LLM 进行动态危机裁决。

    与 resolve_event() 不同，此函数不依赖硬编码的选项列表，
    而是将玩家的任意文本输入作为决策依据，由 LLM 推演后果。

    返回:
        True 表示事件被成功解决
    """
    active_event = st.session_state.get("active_event")
    if not active_event:
        return False

    event_id = active_event.get("id", "")

    event_log = st.session_state.get("event_execution_log", [])
    event_log.append({
        "event_id": event_id,
        "chosen_choice": "_free_text_",
        "player_decision": player_decision[:200],
        "turn": st.session_state.get("turn_number", 0),
    })
    st.session_state.event_execution_log = event_log[-50:]

    resolved = st.session_state.get("resolved_events", [])
    if event_id not in resolved:
        resolved.append(event_id)
        st.session_state.resolved_events = resolved

    from src.events.consequence import execute_crisis_resolution
    execute_crisis_resolution(active_event, player_decision)

    st.session_state.active_event = None
    st.session_state.event_state = "idle"

    return True


def resolve_event(choice_id: str) -> bool:
    """
    玩家做出选择后调用。将选中的 choice 发给 consequence 执行器。

    返回:
        True 表示事件被成功解决
    """
    active_event = st.session_state.get("active_event")
    if not active_event:
        return False

    choices = active_event.get("choices", [])
    selected = next((c for c in choices if c.get("id") == choice_id), None)
    if not selected:
        return False

    event_id = active_event.get("id", "")

    # 记录执行历史（供 condition.py 的 event.X.chosen 引用）
    event_log = st.session_state.get("event_execution_log", [])
    event_log.append({
        "event_id": event_id,
        "chosen_choice": choice_id,
        "turn": st.session_state.get("turn_number", 0),
    })
    st.session_state.event_execution_log = event_log[-50:]

    # 标记为已解决，防止死循环（所有事件只触发一次）
    resolved = st.session_state.get("resolved_events", [])
    if event_id not in resolved:
        resolved.append(event_id)
        st.session_state.resolved_events = resolved

    # 执行后果
    from src.events.consequence import execute_consequence
    execute_consequence(active_event, selected)

    # 重置状态
    st.session_state.active_event = None
    st.session_state.event_state = "idle"

    return True


# ---------------------------------------------------------------------------
# 内部
# ---------------------------------------------------------------------------

def _trigger_event(event: dict) -> None:
    """触发一个事件。"""
    event_type = event.get("type", "audience")

    if event_type == "outcome":
        # 结果型事件：自动执行，不需要玩家选择
        _auto_execute_outcome(event)
    else:
        # 问对型/条件型：等待玩家选择
        st.session_state.active_event = event
        st.session_state.event_state = "awaiting_choice"


def _auto_execute_outcome(event: dict) -> None:
    """自动执行结果型事件（无玩家选择）。"""
    from src.events.consequence import execute_auto_effects
    execute_auto_effects(event)

    # 写入编年史
    narrative = event.get("narrative", "")
    entry = {
        "year": st.session_state.get("year", 0),
        "month": st.session_state.get("month", 1),
        "season": st.session_state.get("season", ""),
        "text": f"【{event.get('title', '事件')}】{narrative}",
        "category": "event",
        "importance": 2,
    }
    chronicle = st.session_state.get("chronicle_log", [])
    chronicle.append(entry)
    st.session_state.chronicle_log = chronicle

    event_id = event.get("id", "")

    # 记录执行
    event_log = st.session_state.get("event_execution_log", [])
    event_log.append({
        "event_id": event_id,
        "chosen_choice": "_auto_",
        "turn": st.session_state.get("turn_number", 0),
    })
    st.session_state.event_execution_log = event_log[-50:]

    # 标记为已解决（所有事件只触发一次）
    resolved = st.session_state.get("resolved_events", [])
    if event_id not in resolved:
        resolved.append(event_id)
        st.session_state.resolved_events = resolved
