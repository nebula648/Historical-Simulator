"""
上帝模式 (创造模式) —— 底层数值修改 + 日志浏览
仅在玩家勾选侧边栏复选框后由 sidebar.py 调用。
"""

from __future__ import annotations

import streamlit as st


def render() -> None:
    """渲染上帝模式面板（扁平结构，无额外包裹层）。"""
    st.markdown("### 🛠️ 上帝模式 (创造模式)")
    st.caption("直接修改游戏底层数据，跳过 LLM 推演与对账。操作记录到天机阁干预日志。")

    tab1, tab2 = st.tabs(["✨ 数值修改", "📋 日志"])

    with tab1:
        from src.devtools.state_editor import render as editor_render
        editor_render()

    with tab2:
        from src.devtools.log_viewer import render as log_render
        log_render()
