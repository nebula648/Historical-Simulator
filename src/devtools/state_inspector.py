"""
天机阁 · 状态查看器（只读）
展示 st.session_state 完整状态树，方便排查数据断层。
"""

from __future__ import annotations

import streamlit as st
from dataclasses import is_dataclass, asdict
from typing import Any


# 敏感 key 过滤（不展示大型二进制或冗余数据）
_FILTER_KEYS = {"_sigma_rule_", "llm_debug_log_raw"}


def render() -> None:
    """渲染只读状态树。"""
    st.markdown("### 🔍 实时状态树")

    view_mode = st.radio("视图", ["关键数据", "全量状态"], horizontal=True, key="inspector_view")

    state_snapshot = _snapshot_state()

    if view_mode == "关键数据":
        _render_key_data(state_snapshot)
    else:
        st.json(state_snapshot)


def _render_key_data(state: dict) -> None:
    """渲染关键数据摘要。"""
    # 时间
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("回合", state.get("turn_number", 0))
    with col2:
        year = state.get("year", 0)
        label = f"公元前{abs(year)}年" if year < 0 else f"公元{year}年"
        st.metric("年份", label)
    with col3:
        st.metric("事件状态", state.get("event_state", "idle"))

    # 资源
    st.markdown("**势力资源**")
    resources = state.get("resources", {})
    if resources:
        for fid, res in resources.items():
            factions = state.get("factions", {})
            f_name = factions.get(fid, {}).get("name", fid) if isinstance(factions, dict) else fid
            st.caption(f"{f_name}: 国库{res.get('treasury',0):,} | 兵力{res.get('manpower',0):,} | 民心{res.get('stability',0)}%")

    # 领土
    st.markdown("**领土分布**")
    territory = state.get("territory", {})
    if territory:
        from collections import Counter
        counts = Counter(territory.values())
        factions = state.get("factions", {})
        for fid, count in counts.most_common():
            f_name = factions.get(fid, {}).get("name", fid) if isinstance(factions, dict) else fid
            st.caption(f"{f_name}: {count} 区")

    # 最近日志
    st.markdown("**最近编年史 (最新 5 条)**")
    chronicle = state.get("chronicle_log", [])
    for entry in chronicle[-5:]:
        text = entry.get("text", str(entry)) if isinstance(entry, dict) else str(entry)
        st.caption(f"• {text[:100]}")


def _snapshot_state() -> dict[str, Any]:
    """生成 session_state 的 JSON 安全快照。"""
    snapshot: dict[str, Any] = {}
    for key in sorted(st.session_state.keys()):
        if key in _FILTER_KEYS or key.startswith("_"):
            continue
        value = st.session_state[key]
        snapshot[key] = _safe_value(value)
    return snapshot


def _safe_value(value: Any, depth: int = 0) -> Any:
    """安全转换值为 JSON 兼容类型。"""
    if depth > 3:
        return "<max depth>"
    if value is None:
        return None
    if isinstance(value, (int, float, str, bool)):
        return value
    if isinstance(value, dict):
        return {k: _safe_value(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        if len(value) > 50:
            return [_safe_value(v, depth + 1) for v in value[:50]] + [f"... ({len(value) - 50} more)"]
        return [_safe_value(v, depth + 1) for v in value]
    if is_dataclass(value):
        return _safe_value(asdict(value), depth + 1)
    return str(type(value).__name__)
