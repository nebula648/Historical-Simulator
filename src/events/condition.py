"""
触发条件求值器 —— 解析并求值 scripted_events 的 trigger.condition 表达式
"""

from __future__ import annotations

import re
from typing import Any

import streamlit as st


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def evaluate_condition(condition_str: str, event_context: dict | None = None) -> bool:
    """
    求值触发条件表达式字符串。

    支持的语法:
      - 比较: year == 1644, month >= 3, turn_number <= 2
      - 逻辑: AND, OR, NOT
      - 事件引用: event.evt_cz_001.chosen == 'choice_call_wu'
      - 势力状态: faction.status == 'active'
      - 区域控制: faction.controls('region_id')
      - 资源阈值: faction.resource > value
      - 括号分组: (A AND B) OR C

    参数:
        condition_str: JSON 中的 condition 字符串
        event_context: 当前事件上下文（用于事件引用）

    返回:
        True/False
    """
    if not condition_str or not condition_str.strip():
        return False

    try:
        return _eval_expr(condition_str.strip(), event_context or {})
    except Exception:
        return False


def poll_events() -> dict | None:
    """
    遍历所有 scripted_events，返回第一个满足触发条件的事件。

    返回:
        事件 dict 或 None
    """
    events = st.session_state.get("scripted_events", [])
    if not events:
        return None

    resolved = set(st.session_state.get("resolved_events", []))

    for evt in events:
        evt_id = evt.get("id", "")
        # 跳过已解决的事件（防止 mandatory/mandatory_choice 事件死循环）
        if evt_id in resolved:
            continue

        trigger = evt.get("trigger", {})
        condition = trigger.get("condition", "")
        priority = trigger.get("priority", "optional")

        if evaluate_condition(condition):
            return evt

    return None


# ---------------------------------------------------------------------------
# 内部：递归下降表达式求值器
# ---------------------------------------------------------------------------

def _eval_expr(expr: str, ctx: dict) -> bool:
    """递归求值表达式。"""
    expr = expr.strip()

    # 处理括号
    if expr.startswith("(") and expr.endswith(")"):
        depth = 0
        for i, c in enumerate(expr):
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            if depth == 0 and i == len(expr) - 1:
                return _eval_expr(expr[1:-1], ctx)

    # 处理 OR（最低优先级）
    or_parts = _split_by_op(expr, " OR ")
    if len(or_parts) > 1:
        return any(_eval_expr(part, ctx) for part in or_parts)

    # 处理 AND
    and_parts = _split_by_op(expr, " AND ")
    if len(and_parts) > 1:
        return all(_eval_expr(part, ctx) for part in and_parts)

    # 处理 NOT
    if expr.startswith("NOT "):
        return not _eval_expr(expr[4:], ctx)

    # 处理原子表达式
    return _eval_atom(expr, ctx)


def _split_by_op(expr: str, op: str) -> list[str]:
    """按逻辑运算符分割，注意不切括号内的内容。"""
    parts: list[str] = []
    depth = 0
    last = 0
    i = 0
    while i < len(expr):
        c = expr[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif depth == 0 and expr[i:i + len(op)] == op:
            parts.append(expr[last:i].strip())
            last = i + len(op)
            i += len(op) - 1
        i += 1
    parts.append(expr[last:].strip())
    return parts


def _eval_atom(atom: str, ctx: dict) -> bool:
    """求值原子比较表达式。"""
    atom = atom.strip()

    # --- 事件引用: event.X.chosen == 'Y' ---
    if atom.startswith("event."):
        return _eval_event_ref(atom)

    # --- 势力区域控制: faction.controls('region') ---
    controls_match = re.match(r"(\w+)\.controls\('([^']+)'\)", atom)
    if controls_match:
        fid = controls_match.group(1)
        region = controls_match.group(2)
        territory = st.session_state.get("territory", {})
        return territory.get(region) == fid

    # --- 一般比较: <left> <op> <right> ---
    return _eval_comparison(atom)


def _eval_event_ref(expr: str) -> bool:
    """求值事件引用如 event.evt_cz_001.chosen == 'choice_call_wu'"""
    # 简化版：直接检查 session_state 中的事件执行记录
    event_log = st.session_state.get("event_execution_log", [])
    for log_entry in event_log:
        event_id = log_entry.get("event_id", "")
        chosen = log_entry.get("chosen_choice", "")
        # 尝试匹配
        if event_id in expr and chosen:
            # 解析: event.X.chosen == 'Y'
            match = re.search(r"event\.(\w+)\.chosen\s*==\s*'(\w+)'", expr)
            if match:
                return match.group(1) == event_id and match.group(2) == chosen
    return False


def _eval_comparison(atom: str) -> bool:
    """求值标准比较表达式。"""
    # 匹配: key op value
    match = re.match(r"(\w[\w.]*)\s*(==|!=|>=|<=|>|<)\s*(.+?)$", atom)
    if not match:
        return False

    var_name = match.group(1)
    op = match.group(2)
    raw_value = match.group(3).strip().strip("'").strip('"')

    actual = _resolve_variable(var_name)

    # 尝试数值比较
    try:
        actual_num = float(actual)
        expected_num = float(raw_value)
        if op == "==":
            return actual_num == expected_num
        elif op == "!=":
            return actual_num != expected_num
        elif op == ">=":
            return actual_num >= expected_num
        elif op == "<=":
            return actual_num <= expected_num
        elif op == ">":
            return actual_num > expected_num
        elif op == "<":
            return actual_num < expected_num
    except (ValueError, TypeError):
        pass

    # 字符串比较
    actual_str = str(actual)
    if op == "==":
        return actual_str == raw_value
    elif op == "!=":
        return actual_str != raw_value
    return False


def _resolve_variable(var_name: str) -> Any:
    """从 st.session_state 中解析变量值。"""
    # 直接 session key
    if var_name in st.session_state:
        return st.session_state[var_name]

    # faction.resource (如 han_empire.manpower)
    if "." in var_name:
        parts = var_name.split(".")
        if len(parts) == 2:
            fid, attr = parts
            # 势力资源
            resources = st.session_state.get("resources", {})
            if attr in ("treasury", "manpower", "food", "stability", "prestige", "corruption"):
                return resources.get(fid, {}).get(attr, 0)
            # 势力状态
            if attr == "status":
                factions = st.session_state.get("factions", {})
                faction = factions.get(fid)
                if faction:
                    return faction.status
            # 势力对象属性
            factions = st.session_state.get("factions", {})
            faction = factions.get(fid)
            if faction and hasattr(faction, attr):
                return getattr(faction, attr)

    return 0
