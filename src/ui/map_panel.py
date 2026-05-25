"""
中央地图面板 —— 封装 Echarts 桥接层调用
"""

from __future__ import annotations

import streamlit as st

from src.map.echarts_bridge import render_strategic_map
from src.map.region_mapper import get_faction_legend


def render() -> None:
    """渲染中央地图区域。"""
    territory = st.session_state.get("territory", {})
    factions = st.session_state.get("factions", {})

    if not territory or not factions:
        st.info("🗺️ 版图数据尚未加载，请先选择剧本。")
        return

    # 沙盘切换占位（双沙盘预留接口）
    sandbox_mode = st.session_state.get("sandbox_mode", "strategic")

    col_ctrl, col_map = st.columns([1, 9])
    with col_ctrl:
        st.caption("🗺️ 沙盘")
        if st.button("🌍", help="天下大势", key="btn_strategic"):
            st.session_state.sandbox_mode = "strategic"
        if st.button("🔍", help="局部战区（待实现）", key="btn_tactical"):
            st.session_state.sandbox_mode = "tactical"

    with col_map:
        if sandbox_mode == "strategic":
            render_strategic_map(territory, factions)
        else:
            st.info("局部战区视图将在后续版本中实现。")

    # 势力图例
    _render_legend(factions)


def _render_legend(factions: dict) -> None:
    """在地图下方渲染势力颜色图例。"""
    legend = get_faction_legend(factions)
    if not legend:
        return

    cols = st.columns(len(legend))
    for i, item in enumerate(legend):
        with cols[i]:
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:6px;padding:4px 0;'>"
                f"<span style='width:14px;height:14px;border-radius:3px;"
                f"background:{item['color']};display:inline-block;'></span>"
                f"<span style='font-size:13px;color:#E0E0E0;'>{item['name']}</span>"
                f"<span style='font-size:11px;color:#888;'>({item['regions']}区)</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
