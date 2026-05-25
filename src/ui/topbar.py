"""
顶部状态栏 —— 横向平铺核心资源与当前日期
"""

from __future__ import annotations

import streamlit as st

# 资源 key → 显示标签（中文）映射
RESOURCE_LABEL: dict[str, str] = {
    "treasury":   "国库",
    "manpower":   "兵力",
    "food":       "粮草",
    "stability":  "民心",
    "prestige":   "威望",
    "corruption": "腐败度",
}

# 资源顯示順序
RESOURCE_ORDER = ["treasury", "manpower", "food", "stability", "prestige", "corruption"]

# 资源格式化函数映射
_RESOURCE_FORMATTER: dict[str, callable] = {
    "treasury":   lambda v: f"{v:,} 两",
    "manpower":   lambda v: f"{v:,} 人",
    "food":       lambda v: f"{v:,} 石",
    "stability":  lambda v: f"{v}%",
    "prestige":   lambda v: f"{v}%",
    "corruption": lambda v: f"{v}%",
}

# 阈值颜色规则: (危险阈值, 警告阈值, 反向标志)
# 反向标志=True 表示值越低越好（如腐败度）
_THRESHOLD_RULES: dict[str, tuple[int, int, bool]] = {
    "stability":  (25, 50, False),
    "prestige":   (25, 50, False),
    "corruption": (75, 50, True),
    "manpower":   (10000, 30000, False),
    "treasury":   (5000, 15000, False),
    "food":       (3000, 10000, False),
}


def _delta_color(key: str, value: int) -> str:
    """根据阈值规则返回 st.metric 的 delta_color。"""
    rule = _THRESHOLD_RULES.get(key)
    if rule is None:
        return "normal"
    danger, warning, inverted = rule
    if inverted:
        if value >= danger:
            return "inverse"
        elif value >= warning:
            return "off"
        else:
            return "normal"
    else:
        if value <= danger:
            return "inverse"
        elif value <= warning:
            return "off"
        else:
            return "normal"


def render() -> None:
    """渲染顶部状态栏。"""
    player_faction = st.session_state.get("player_faction")
    if not player_faction:
        st.warning("未选择剧本")
        return

    resources = st.session_state.get("resources", {}).get(player_faction, {})
    year = st.session_state.get("year", 0)
    month = st.session_state.get("month", 1)
    season = st.session_state.get("season", "春")
    scenario_title = st.session_state.get("scenario_title", "")

    # 年份格式
    if year < 0:
        year_str = f"公元前 {abs(year)}"
    else:
        year_str = f"公元 {year}"

    date_str = f"{year_str}年 {month}月（{season}）"

    # 动态列宽：日期 1 + 资源 N 列 + 回合数 1
    n_cols = len(RESOURCE_ORDER) + 2
    cols = st.columns(n_cols)

    # 第一列：日期
    with cols[0]:
        st.markdown(f"**📅 {date_str}**")
        st.caption(f"回合 {st.session_state.get('turn_number', 0)}")

    # 中间：资源
    for i, key in enumerate(RESOURCE_ORDER):
        value = resources.get(key, 0)
        label = RESOURCE_LABEL.get(key, key)
        formatted = _RESOURCE_FORMATTER.get(key, lambda v: str(v))(value)
        delta_c = _delta_color(key, value)

        with cols[i + 1]:
            st.metric(
                label=label,
                value=formatted,
                delta=None,
                delta_color=delta_c,
            )

    # 最后一列：剧本标题
    with cols[-1]:
        st.markdown(f"**🏯 {scenario_title}**")
        faction = st.session_state.get("factions", {}).get(player_faction)
        if faction:
            st.caption(f"扮演: {faction.name}")
