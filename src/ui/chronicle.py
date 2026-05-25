"""
底部编年史 —— 时间线滚动日志
"""

from __future__ import annotations

import streamlit as st


# 事件分类 → 图标 + 颜色
CATEGORY_STYLE: dict[str, tuple[str, str]] = {
    "system":     ("📢", "#888888"),
    "military":   ("⚔️", "#FF6B6B"),
    "diplomacy":  ("🌐", "#4ECDC4"),
    "economy":    ("💰", "#FFD93D"),
    "event":      ("📜", "#C44BED"),
    "general":    ("📝", "#E0E0E0"),
}


def render() -> None:
    """渲染底部编年史区域。"""
    st.divider()
    st.subheader("📜 编年史")

    chronicle = st.session_state.get("chronicle_log", [])

    if not chronicle:
        st.caption("天下尚未发生大事……")
        return

    # 只显示最近 50 条
    recent = chronicle[-50:]

    # 渲染为紧凑的时间线
    for entry in reversed(recent):
        # 兼容 dict 和 dataclass
        if isinstance(entry, dict):
            year = entry.get("year", 0)
            month = entry.get("month", 1)
            text = entry.get("text", "")
            category = entry.get("category", "general")
        else:
            year = getattr(entry, "year", 0)
            month = getattr(entry, "month", 1)
            text = getattr(entry, "text", "")
            category = getattr(entry, "category", "general")

        icon, color = CATEGORY_STYLE.get(category, ("📝", "#E0E0E0"))

        if year < 0:
            date_str = f"公元前{abs(year)}年{month}月"
        else:
            date_str = f"公元{year}年{month}月"

        st.markdown(
            f"<span style='color:{color}'>{icon}</span> "
            f"<small style='color:#888'>{date_str}</small> "
            f"{text}",
            unsafe_allow_html=True,
        )
