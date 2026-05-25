"""
剧本选择页 —— 时间节点卡片选择器
"""

from __future__ import annotations

import html

import streamlit as st

from src.scenario.loader import list_scenarios, load_scenario
from src.llm.client import is_api_key_configured


def render() -> None:
    """渲染剧本选择页。"""
    st.markdown("# ⏳ 历史模拟器")
    st.markdown("### 选择一个时间节点，改写历史走向")

    st.markdown("---")

    scenarios = list_scenarios()

    # 二次过滤：确保所有条目都有合法 ID 和标题
    scenarios = [
        s for s in scenarios
        if s.get("id") and s.get("title")
        and not s["id"].startswith("geography_manifest")
        and not s["title"].startswith("geography_manifest")
    ]

    if not scenarios:
        st.warning("未找到任何剧本文件。请检查 `scenarios/` 目录。")
        return

    # 按年代排序
    scenarios.sort(key=lambda s: s["start_year"])

    cols = st.columns(min(len(scenarios), 3))

    for i, scenario in enumerate(scenarios):
        col_idx = i % len(cols)
        with cols[col_idx]:
            _render_scenario_card(scenario)


def _render_scenario_card(scenario: dict) -> None:
    """渲染单张剧本卡片。所有动态文本均经 html.escape 防注入。"""
    start_year = scenario["start_year"]
    if start_year < 0:
        year_label = f"公元前 {abs(start_year)} 年"
    else:
        year_label = f"公元 {start_year} 年"

    # 安全转义所有动态文本
    title_safe = html.escape(scenario["title"])
    era_safe = html.escape(scenario.get("era", ""))
    subtitle_safe = html.escape(scenario.get("subtitle", ""))
    desc_text = scenario.get("description", "")
    desc_safe = html.escape(desc_text[:120])
    desc_ellipsis = html.escape(desc_text[120:180]) if len(desc_text) > 120 else ""

    # 卡片样式 —— 使用转义后的文本
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #16213E 0%, #1A1A2E 100%);
        border: 1px solid #3A3A5E;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 12px;
    ">
        <h3 style="margin:0 0 6px 0; color:#E0E0E0;">{title_safe}</h3>
        <p style="color:#C41E3A; margin:0 0 8px 0; font-size:14px;">
            {year_label} · {era_safe}
        </p>
        <p style="color:#AAA; font-size:13px; margin:0 0 10px 0;">
            {subtitle_safe}
        </p>
        <p style="color:#888; font-size:12px; line-height:1.5;">
            {desc_safe}{desc_ellipsis}...
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 开始按钮
    btn_label = f"⚔️ 进入 {year_label}"
    no_key = not _check_api_key()
    if st.button(btn_label, key=f"btn_{scenario['id']}", type="primary", use_container_width=True,
                 disabled=no_key):
        if not _check_api_key():
            st.warning("⚠️ 启动失败：检测到当前圣旨缺乏天机能量（未配置有效的 API Key），请在侧边栏「🔑 LLM 驱动引擎配置」中注入密钥！")
        else:
            load_scenario(scenario["id"])
            st.session_state.page = "game_main"
            st.rerun()


def _check_api_key() -> bool:
    """检查 API Key 是否已配置，封装 is_api_key_configured 供 UI 层使用。"""
    return is_api_key_configured()
