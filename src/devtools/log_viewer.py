"""
天机阁 · 日志浏览器
展示 LLM 通信原始日志 + 对账警告差异记录
"""

from __future__ import annotations

import streamlit as st


def render() -> None:
    """渲染日志浏览器。"""
    st.markdown("### 📋 底层日志")

    tab1, tab2, tab3 = st.tabs(["🤖 LLM 通信日志", "🔴 对账报告", "🛡️ 干预日志"])

    with tab1:
        _render_llm_logs()

    with tab2:
        _render_reconciliation_logs()

    with tab3:
        _render_intervention_logs()


# ---------------------------------------------------------------------------
# LLM 通信日志
# ---------------------------------------------------------------------------

def _render_llm_logs() -> None:
    debug_log = st.session_state.get("llm_debug_log", [])
    if not debug_log:
        st.caption("暂无 LLM 通信记录。")
        return

    for i, entry in enumerate(reversed(debug_log)):
        turn = entry.get("turn", "?")
        with st.expander(f"回合 {turn} — LLM 通信 #{len(debug_log) - i}", expanded=(i == 0)):
            st.caption(f"**回合:** {turn}")

            sp = entry.get("system_prompt", "")
            up = entry.get("user_prompt", "")
            resp = entry.get("raw_response", "")

            col1, col2 = st.columns(2)
            with col1:
                st.metric("System Prompt", f"{len(sp)} 字符")
            with col2:
                st.metric("User Prompt", f"{len(up)} 字符")

            with st.expander("System Prompt"):
                st.code(sp, language="markdown")
            with st.expander("User Prompt"):
                st.code(up, language="markdown")
            with st.expander("LLM 原始响应"):
                st.code(resp, language="markdown")


# ---------------------------------------------------------------------------
# 对账报告
# ---------------------------------------------------------------------------

def _render_reconciliation_logs() -> None:
    reports = st.session_state.get("reconciliation_reports", [])
    if not reports:
        st.success("暂无对账记录——所有回合均通过数值对账。")
        return

    clean_count = sum(1 for r in reports if (
        r.is_clean if hasattr(r, 'is_clean') else r.get('is_clean', True)
    ))
    dirty_count = len(reports) - clean_count

    col1, col2 = st.columns(2)
    with col1:
        st.metric("通过", clean_count)
    with col2:
        st.metric("异常", dirty_count, delta=None if dirty_count == 0 else f"-{dirty_count}")

    for i, report in enumerate(reversed(reports)):
        is_clean = report.is_clean if hasattr(report, 'is_clean') else report.get('is_clean', True)
        turn = report.turn if hasattr(report, 'turn') else report.get('turn', '?')
        used_fb = report.used_fallback if hasattr(report, 'used_fallback') else report.get('used_fallback', False)

        icon = "✅" if is_clean else "🔴"
        suffix = " [嗅探器兜底]" if used_fb else ""

        with st.expander(f"{icon} 回合 {turn} — 对账报告{suffix}", expanded=not is_clean):
            claimed = report.claimed_effects if hasattr(report, 'claimed_effects') else report.get('claimed_effects', {})
            actual = report.actual_deltas if hasattr(report, 'actual_deltas') else report.get('actual_deltas', {})

            c1, c2 = st.columns(2)
            with c1:
                st.caption("**LLM 声称**")
                st.json(claimed)
            with c2:
                st.caption("**引擎实际**")
                st.json(actual)

            discrepancies = report.discrepancies if hasattr(report, 'discrepancies') else report.get('discrepancies', [])
            if discrepancies:
                st.error("差异详情：")
                for d in discrepancies:
                    st.caption(f"  • {d}")


# ---------------------------------------------------------------------------
# 干预日志
# ---------------------------------------------------------------------------

def _render_intervention_logs() -> None:
    interventions = st.session_state.get("intervention_log", [])
    if not interventions:
        st.caption("暂无天机阁手动干预记录。")
        return

    st.caption(f"共 {len(interventions)} 条干预记录")
    for entry in reversed(interventions):
        time = entry.get("time", "")[:19]
        action = entry.get("action", "")
        detail = entry.get("detail", "")
        turn = entry.get("turn", "?")
        st.caption(f"`{time}` 回合{turn} | **{action}** | {detail}")
