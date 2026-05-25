"""
御前问对 —— 事件对话框 UI
当事件状态机变为 awaiting_choice 时，在主界面顶部渲染自由文本危机决策界面。
彻底废除硬编码选项，玩家可输入任意应对策略。
"""

from __future__ import annotations

import streamlit as st

from src.llm.client import is_api_key_configured


def render() -> None:
    """若有待处理事件，在页面顶部渲染事件对话框。"""
    if st.session_state.get("event_state") != "awaiting_choice":
        return

    active_event = st.session_state.get("active_event")
    if not active_event:
        return

    event_type = active_event.get("type", "audience")
    title = active_event.get("title", "大事发生")
    narrative = active_event.get("narrative", "")

    if event_type == "outcome":
        _render_outcome(active_event)
        return

    with st.container():
        st.markdown("---")
        st.markdown(f"## ⚡ {title}")

        st.markdown(f"""
        <div style="
            background: #F5F0E8;
            border: 2px solid #C41E3A;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 16px;
            font-size: 15px;
            line-height: 1.8;
            color: #1A1A1A;
            white-space: pre-wrap;
        ">
        {narrative}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 📜 请陛下圣裁")
        st.caption(
            "面对此危机，陛下可下达任意旨意——"
            "无论是合纵连横的奇策，还是一意孤行的荒唐之举，历史都将如实记录其后果。"
        )

        no_key = not is_api_key_configured()
        player_decision = st.text_area(
            "圣断",
            placeholder="请陛下圣裁（可输入任意应对之策）：",
            label_visibility="collapsed",
            height=120,
            key=f"crisis_input_{active_event.get('id')}",
            disabled=no_key,
        )

        if st.button(
            "⚡ 下达圣断",
            key=f"crisis_submit_{active_event.get('id')}",
            use_container_width=True,
            type="primary",
            disabled=no_key,
        ):
            if not player_decision.strip():
                st.warning("陛下，请至少留下只言片语……")
            elif not is_api_key_configured():
                st.warning("⚠️ 启动失败：检测到当前圣旨缺乏天机能量（未配置有效的 API Key），请在侧边栏「🔑 LLM 驱动引擎配置」中注入密钥！")
            else:
                from src.events.state_machine import resolve_event_with_decision
                resolve_event_with_decision(player_decision.strip())
                st.rerun()


def _render_outcome(event: dict) -> None:
    """渲染 outcome 型事件（自动执行，无需玩家选择）。"""
    if not is_api_key_configured():
        st.warning("⚠️ 未配置 API Key，无法自动处理事件。请在侧边栏注入密钥后刷新。")
        return
    st.info("此事件将自动处理……")
    from src.events.state_machine import resolve_event
    resolve_event("_auto_")
    st.rerun()
