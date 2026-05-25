"""
左侧控制台 —— 势力详情、军事结构、外交关系、史官纠错、上帝模式
"""

from __future__ import annotations

import streamlit as st

from src.config.era_naming import get_era_naming

# ---------------------------------------------------------------------------
# 英文 key → 中文 映射字典（防止乱码）
# ---------------------------------------------------------------------------

UNIT_TYPE_MAP: dict[str, str] = {
    "步兵":       "步兵",
    "骑兵":       "骑兵",
    "精锐步兵":   "精锐步兵",
    "精锐骑兵":   "精锐骑兵",
    "混合部队":   "混合部队",
    "民兵":       "民兵",
    "水师":       "水师",
    "火器营":     "火器营",
    "elite_infantry":   "精锐步兵",
    "elite_cavalry":    "精锐骑兵",
    "infantry":         "步兵",
    "cavalry":          "骑兵",
    "mixed":            "混合部队",
    "militia":          "民兵",
    "navy":             "水师",
    "artillery":        "火器营",
}

GOVERNMENT_MAP: dict[str, str] = {
    "中央集权帝国":       "中央集权帝国",
    "中央集权郡县制":     "中央集权郡县制",
    "部落联盟":           "部落联盟",
    "部落联盟向帝制过渡": "部落联盟→帝制",
    "封建王国":           "封建王国",
    "藩属国":             "藩属国",
    "起义政权":           "起义政权",
    "军阀割据":           "军阀割据",
}

DIPLOMACY_STATUS_MAP: dict[str, str] = {
    "war":       "⚔️ 战争",
    "peace":     "🕊️ 和平",
    "alliance":  "🤝 同盟",
    "vassal":    "🏴 藩属",
    "tributary": "🎁 朝贡",
    "neutral":   "➖ 中立",
}

RESOURCE_LABEL_MAP: dict[str, str] = {
    "treasury":   "国库",
    "manpower":   "兵力",
    "food":       "粮草",
    "stability":  "民心",
    "prestige":   "威望",
    "corruption": "腐败度",
}


# ---------------------------------------------------------------------------
# 公共入口
# ---------------------------------------------------------------------------

def render() -> None:
    """渲染左侧边栏全部内容。"""
    era = get_era_naming()

    # ---- 0. 返回剧本选择 ----
    if st.sidebar.button("⬅️ 返回剧本选择", use_container_width=True,
                         key="btn_back_to_picker"):
        st.session_state.page = "scenario_picker"
        st.rerun()

    # ---- 1. 史官驳回（常驻置顶，始终可见） ----
    _render_correction_panel(era)

    st.sidebar.markdown(f"# {era.power_center}")

    player_faction = st.session_state.get("player_faction")
    factions = st.session_state.get("factions", {})

    if not player_faction or player_faction not in factions:
        st.sidebar.warning("暂无势力数据")
        return

    _render_player_info(factions[player_faction])
    _render_military(factions[player_faction])
    _render_all_factions(factions)
    _render_diplomacy()

    # ---- 系统菜单 ----
    _render_system_menu()

    # ---- 上帝模式（创造模式） ----
    _render_god_mode()


# ---------------------------------------------------------------------------
# 0. 史官驳回 —— AI 逻辑纠错（常驻置顶）
# ---------------------------------------------------------------------------

def _render_correction_panel(era) -> None:
    """在侧边栏最上方渲染常驻纠错入口。"""
    snapshot = st.session_state.get("last_turn_snapshot")
    has_snapshot = snapshot is not None

    label = "⚠️ 史官驳回 (AI 逻辑纠错)"
    if not has_snapshot:
        label = "⚠️ 史官驳回 (暂无回滚点)"

    with st.sidebar.expander(label, expanded=False):
        if not has_snapshot:
            st.info("请先执行一次推演，系统将自动捕获状态快照，之后即可使用纠错功能。")
            return

        snap_turn = snapshot.get("turn_number", "?")
        st.info(f"📸 可回滚至第 {snap_turn} 回合之前。")

        # 上次推演预览
        last_result = st.session_state.get("last_turn_result")
        if last_result and last_result.get("ok"):
            narrative = last_result.get("narrative", "")
            is_macro = last_result.get("years_advanced", 0) > 0
            mode = last_result.get("mode", "")
            tag = " [已纠错]" if "corrected" in mode else ""
            turn_type = f"宏观{last_result.get('years_advanced', 0)}年" if is_macro else "微观回合"
            st.caption(f"上一回合: {turn_type}{tag}")
            with st.container(border=True):
                st.markdown(
                    f"<div style='max-height:120px;overflow-y:auto;font-size:11px;"
                    f"line-height:1.5;color:#666;'>{narrative[:400]}</div>",
                    unsafe_allow_html=True,
                )

        placeholder_lines = era.correction_placeholder_lines
        placeholder_text = "例如：\n" + "\n".join(placeholder_lines)

        correction = st.text_area(
            "指出推演谬误，要求重写：",
            value="",
            height=80,
            placeholder=placeholder_text,
            key="sidebar_correction_input",
            label_visibility="collapsed",
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔴 打回重推", type="secondary",
                         disabled=not correction.strip(),
                         use_container_width=True,
                         key="btn_sidebar_regenerate_micro"):
                from src.simulation.micro_turn import regenerate_with_correction
                with st.spinner("🔄 回滚中……"):
                    result = regenerate_with_correction(correction.strip())
                st.session_state.last_turn_result = result
                st.rerun()

        with c2:
            is_macro = (
                st.session_state.get("last_turn_result", {})
                .get("years_advanced", 0) > 0
            )
            if st.button("🔴 重推宏指令", type="secondary",
                         disabled=not correction.strip() or not is_macro,
                         use_container_width=True,
                         key="btn_sidebar_regenerate_macro"):
                from src.simulation.macro_turn import regenerate_macro_with_correction
                with st.spinner("🔄 回滚宏观飞跃中……"):
                    result = regenerate_macro_with_correction(correction.strip())
                st.session_state.last_turn_result = result
                st.rerun()

        # 快速模板
        with st.expander("📋 快速纠错模板", expanded=False):
            quick_fixes = [
                "请确认当前首都的实际位置，并基于此修正势力版图。",
                "以下势力已不存在，请勿在叙事中引用：",
                "请注意以下将领的存活状态：",
                "版图归属错误，实际上该区域当前归属为：",
            ]
            for qf in quick_fixes:
                if st.button(f"📋 {qf}", key=f"sidebar_qf_{qf[:15]}",
                             use_container_width=True):
                    st.session_state.sidebar_correction_input = qf
                    st.rerun()


# ---------------------------------------------------------------------------
# 玩家势力信息
# ---------------------------------------------------------------------------

def _render_player_info(faction) -> None:
    """渲染玩家势力基本信息。"""
    gov_label = GOVERNMENT_MAP.get(faction.government, faction.government)

    with st.sidebar.expander(f"👑 {faction.name} · {faction.ruler}", expanded=True):
        st.markdown(f"""
        | 属性 | 值 |
        |------|-----|
        | 君主 | **{faction.ruler}**（{faction.ruler_title}） |
        | 政体 | {gov_label} |
        | 首都 | `{faction.capital}` |
        | 国色 | 🟨 `{faction.color}` |
        """)
        if faction.description:
            st.caption(faction.description)


# ---------------------------------------------------------------------------
# 军事结构
# ---------------------------------------------------------------------------

def _render_military(faction) -> None:
    """渲染玩家势力的军事结构。"""
    military = faction.military if hasattr(faction, 'military') else []
    if not military:
        return

    total_men = sum(u.size for u in military)
    avg_morale = sum(u.morale for u in military) / len(military) if military else 0

    with st.sidebar.expander(f"⚔️ 军事力量（总兵力 {total_men:,} · 均士气 {avg_morale:.0f}）", expanded=True):
        for unit in military:
            unit_type_cn = UNIT_TYPE_MAP.get(unit.unit_type, unit.unit_type)
            morale_color = "🟢" if unit.morale >= 70 else ("🟡" if unit.morale >= 40 else "🔴")
            st.markdown(f"""
            **{unit.name}** `{unit.location}`
            - 🏷️ {unit_type_cn} | 👥 {unit.size:,}人 | {morale_color} 士气 {unit.morale}
            - 🧑‍✈️ 将领: {unit.general or '无'}
            ---
            """)


# ---------------------------------------------------------------------------
# 全势力概览
# ---------------------------------------------------------------------------

def _render_all_factions(factions: dict) -> None:
    """渲染所有势力概览。"""
    with st.sidebar.expander("🗺️ 天下势力", expanded=False):
        for fid, faction in factions.items():
            resources = faction.resources if hasattr(faction, 'resources') else {}
            manpower = resources.get("manpower", 0)
            stability = resources.get("stability", 0)
            status_icon = "🟢" if faction.is_alive else "💀"
            st.markdown(
                f"{status_icon} **{faction.name}** | "
                f"👥 {manpower:,} | 🏛️ 民心 {stability}%"
            )


# ---------------------------------------------------------------------------
# 外交关系
# ---------------------------------------------------------------------------

def _render_diplomacy() -> None:
    """渲染外交关系矩阵。"""
    diplomacy = st.session_state.get("diplomacy", [])
    if not diplomacy:
        return

    factions = st.session_state.get("factions", {})
    player_faction = st.session_state.get("player_faction")

    with st.sidebar.expander("🌐 天下外交", expanded=False):
        for rel in diplomacy:
            a = rel.faction_a if hasattr(rel, 'faction_a') else rel.get('faction_a', '')
            b = rel.faction_b if hasattr(rel, 'faction_b') else rel.get('faction_b', '')
            status = rel.status if hasattr(rel, 'status') else rel.get('status', '')
            tension = rel.tension if hasattr(rel, 'tension') else rel.get('tension', 0)

            if player_faction not in (a, b):
                continue

            other = b if a == player_faction else a
            other_faction = factions.get(other)
            other_name = other_faction.name if other_faction else other
            status_cn = DIPLOMACY_STATUS_MAP.get(status, status)
            tension_bar = "█" * (tension // 10) + "░" * (10 - tension // 10)

            st.markdown(f"**{other_name}**: {status_cn}")
            st.progress(tension / 100, text=f"紧张度 {tension}/100")


# ---------------------------------------------------------------------------
# 系统菜单：存档 / 读档
# ---------------------------------------------------------------------------

def _render_system_menu() -> None:
    """渲染系统菜单：保存/读取存档。"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💾 系统菜单")

    from src.session.save_manager import list_saves, save_game, load_game, delete_save

    # ---- 保存 ----
    with st.sidebar.expander("💾 保存游戏", expanded=False):
        auto_name = _auto_save_name()
        slot_name = st.text_input("存档名称", value=auto_name, key="save_slot_name")
        if st.button("📥 保存", use_container_width=True, key="btn_save"):
            path = save_game(slot_name)
            st.success(f"已保存到: {slot_name}")
            st.caption(f"路径: `{path}`")

    # ---- 读取 ----
    with st.sidebar.expander("📂 读取存档", expanded=False):
        saves = list_saves()
        if not saves:
            st.caption("暂无存档")
        else:
            for s in saves:
                slot = s["slot_name"]
                year = s.get("year", 0)
                if year < 0:
                    year_str = f"公元前{abs(year)}年"
                else:
                    year_str = f"公元{year}年"
                title = s.get("scenario_title", "")
                turn = s.get("turn_number", 0)

                col1, col2 = st.columns([5, 1])
                with col1:
                    if st.button(f"📂 {title} — {year_str} (回合{turn})",
                                 key=f"load_{slot}", use_container_width=True):
                        load_game(slot)
                        st.success(f"已加载: {slot}")
                        st.rerun()
                with col2:
                    if st.button("🗑️", key=f"del_{slot}", help="删除此存档"):
                        delete_save(slot)
                        st.rerun()


def _auto_save_name() -> str:
    """生成自动存档名。"""
    sid = st.session_state.get("scenario_id", "unknown")
    turn = st.session_state.get("turn_number", 0)
    year = st.session_state.get("year", 0)
    month = st.session_state.get("month", 1)
    return f"{sid}_turn{turn}_y{year}m{month}"


# ---------------------------------------------------------------------------
# 上帝模式 (创造模式) —— 仅在勾选时展示
# ---------------------------------------------------------------------------

def _render_god_mode() -> None:
    """渲染上帝模式入口。仅当玩家主动勾选复选框时才显示修改器。"""
    st.sidebar.markdown("---")
    god_mode = st.sidebar.checkbox(
        "🛠️ 上帝模式 (创造模式)",
        value=False,
        key="sidebar_god_mode",
        help="勾选后将显示底层数值修改器与日志浏览器",
    )
    if god_mode:
        from src.devtools.panel import render as panel_render
        panel_render()
