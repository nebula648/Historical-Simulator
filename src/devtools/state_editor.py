"""
天机阁 · 超级修改器（读写）
允许跳过 LLM，直接通过 UI 表单强制修改数值和版图。
"""

from __future__ import annotations

import streamlit as st

from src.engine.resource import add_resource, subtract_resource
from src.map.territory_evolver import apply_territory_changes


def render() -> None:
    """渲染超级修改器面板（兜底手段）。"""
    st.markdown("### ✨ 创造模式 — 底层数值直接修改")
    st.caption("⚠️ 此为【兜底手段】。优先使用「逻辑纠错与重推」让 AI 自我修正；仅在 AI 反复犯错或需要微调时使用此处。")
    st.caption("所有修改跳过 LLM 推演和数值对账，直接写入引擎。操作记录到天机阁干预日志。")

    tab_a, tab_b = st.tabs(["💰 资源修改", "🗺️ 版图修改"])

    with tab_a:
        _render_resource_editor()

    with tab_b:
        _render_territory_editor()


# ---------------------------------------------------------------------------
# 资源修改
# ---------------------------------------------------------------------------

def _render_resource_editor() -> None:
    factions = st.session_state.get("factions", {})
    if not factions:
        st.info("无可用势力")
        return

    faction_names = {fid: f.name for fid, f in factions.items()}
    selected_fid = st.selectbox(
        "选择势力",
        options=list(faction_names.keys()),
        format_func=lambda fid: f"{faction_names[fid]} ({fid})",
        key="editor_select_faction",
    )

    if not selected_fid:
        return

    current_res = st.session_state.get("resources", {}).get(selected_fid, {})
    st.caption(f"当前: 国库 {current_res.get('treasury', 0):,} | "
                f"兵力 {current_res.get('manpower', 0):,} | "
                f"粮草 {current_res.get('food', 0):,}")

    col1, col2, col3 = st.columns(3)

    with col1:
        treasury_delta = st.number_input("国库变动", value=0, step=1000, key="edit_treasury")
        if st.button("应用国库", key="btn_treasury"):
            _apply_resource(selected_fid, "treasury", treasury_delta)

    with col2:
        manpower_delta = st.number_input("兵力变动", value=0, step=5000, key="edit_manpower")
        if st.button("应用兵力", key="btn_manpower"):
            _apply_resource(selected_fid, "manpower", manpower_delta)

    with col3:
        food_delta = st.number_input("粮草变动", value=0, step=5000, key="edit_food")
        if st.button("应用粮草", key="btn_food"):
            _apply_resource(selected_fid, "food", food_delta)

    col4, col5, col6 = st.columns(3)

    with col4:
        stability_val = st.slider("民心", 0, 100, current_res.get("stability", 50), key="edit_stability")
        if st.button("设置民心", key="btn_stability"):
            _set_resource(selected_fid, "stability", stability_val)

    with col5:
        prestige_val = st.slider("威望", 0, 100, current_res.get("prestige", 50), key="edit_prestige")
        if st.button("设置威望", key="btn_prestige"):
            _set_resource(selected_fid, "prestige", prestige_val)

    with col6:
        corruption_val = st.slider("腐败度", 0, 100, current_res.get("corruption", 50), key="edit_corruption")
        if st.button("设置腐败", key="btn_corruption"):
            _set_resource(selected_fid, "corruption", corruption_val)


# ---------------------------------------------------------------------------
# 版图修改
# ---------------------------------------------------------------------------

def _render_territory_editor() -> None:
    territory = st.session_state.get("territory", {})
    factions = st.session_state.get("factions", {})

    if not territory:
        st.info("无可用版图数据")
        return

    faction_names = {fid: f.name for fid, f in factions.items()}
    faction_names["neutral"] = "无主之地"

    # 区域列表
    all_regions = sorted(territory.keys())
    selected_region = st.selectbox(
        "选择区域",
        options=all_regions,
        format_func=lambda r: f"{r} (当前: {faction_names.get(territory.get(r, 'neutral'), territory.get(r, 'neutral'))})",
        key="editor_select_region",
    )

    if selected_region:
        current_owner = territory.get(selected_region, "neutral")
        current_name = faction_names.get(current_owner, current_owner)
        st.caption(f"当前归属: **{current_name}**")

        new_owner = st.selectbox(
            "新归属",
            options=list(faction_names.keys()),
            format_func=lambda fid: faction_names[fid],
            key="editor_new_owner",
        )

        reason = st.text_input("变更原因", value="天机阁手动修改", key="editor_reason")

        if st.button("⚡ 执行版图变更", type="primary", key="btn_territory"):
            if new_owner != current_owner:
                applied = apply_territory_changes([{
                    "region_id": selected_region,
                    "to_faction": new_owner,
                    "reason": f"[天机阁] {reason}",
                }])
                if applied:
                    _log_intervention("版图修改", f"{selected_region}: {current_owner} → {new_owner}")
                    st.success(f"{selected_region} 已归属 {faction_names.get(new_owner, new_owner)}")
                    st.rerun()


# ---------------------------------------------------------------------------
# 内部
# ---------------------------------------------------------------------------

def _apply_resource(faction_id: str, key: str, delta: int) -> None:
    if delta > 0:
        add_resource(faction_id, key, delta, reason="天机阁手动增加")
    elif delta < 0:
        subtract_resource(faction_id, key, abs(delta), reason="天机阁手动减少")
    else:
        return
    _log_intervention("资源修改", f"{faction_id}.{key}: {delta:+d}")
    st.success(f"已应用 {key} {delta:+d}")
    st.rerun()


def _set_resource(faction_id: str, key: str, value: int) -> None:
    resources = st.session_state.get("resources", {})
    current = resources.get(faction_id, {}).get(key, 0)
    delta = value - current
    if delta > 0:
        add_resource(faction_id, key, delta, reason="天机阁设值")
    elif delta < 0:
        subtract_resource(faction_id, key, abs(delta), reason="天机阁设值")
    _log_intervention("资源设值", f"{faction_id}.{key} = {value}")
    st.success(f"已设置 {key} = {value}")
    st.rerun()


def _log_intervention(action: str, detail: str) -> None:
    """记录天机阁干预日志。"""
    log = st.session_state.get("intervention_log", [])
    from datetime import datetime
    log.append({
        "time": datetime.now().isoformat(),
        "action": action,
        "detail": detail,
        "turn": st.session_state.get("turn_number", 0),
    })
    st.session_state.intervention_log = log[-50:]
