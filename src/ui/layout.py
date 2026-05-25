"""
总体布局编排 —— 宽屏 Grid 划分调度
"""

from __future__ import annotations

import streamlit as st

from src.ui import topbar, sidebar, chronicle, map_panel, event_dialog
from src.config.era_naming import get_era_naming
from src.llm.client import is_api_key_configured


def render_game_main() -> None:
    """渲染游戏主页面完整布局。"""
    page = st.session_state.get("page")
    if page != "game_main":
        return

    scenario_title = st.session_state.get("scenario_title", "历史模拟器")
    st.title(f"🏯 {scenario_title}")

    # ---- 第 0 行：事件对话框（如有待处理事件，在此渲染） ----
    event_dialog.render()

    # ---- 第 1 行：顶部状态栏 ----
    topbar.render()

    st.divider()

    # ---- 第 2 行：左侧控制台 + 中央地图 ----
    col_left, col_center = st.columns([2, 8])

    with col_left:
        _render_command_panel()

    with col_center:
        map_panel.render()

    # ---- 第 3 行：底部编年史 ----
    chronicle.render()

    # 边栏（始终渲染在 st.sidebar 中）
    sidebar.render()


# ---------------------------------------------------------------------------
# 政令面板
# ---------------------------------------------------------------------------

def _render_command_panel() -> None:
    """左侧政令输入与反馈区。"""
    era = get_era_naming()
    event_blocked = st.session_state.get("event_state") == "awaiting_choice"
    has_intel = bool(era.intel_org and era.intel_org.strip())
    no_key = not is_api_key_configured()

    # 安全性：若当前时代无情报机构，但 session 中残留了 secret_operation，则回退为公开诏令
    if not has_intel and st.session_state.get("action_type") == "secret_operation":
        st.session_state.action_type = "public_edict"

    # ---- 双选项卡：政务 / 御前召见 ----
    tab_gov, tab_audience = st.tabs([
        era.command_panel_gov_tab,
        era.command_panel_audience_tab,
    ])

    # ===== 选项卡 1：处理政务 =====
    with tab_gov:
        action_options = ["public_edict"]
        action_labels = {
            "public_edict": "📜 公开诏令 (影响全局)",
        }
        if has_intel:
            action_options.append("secret_operation")
            action_labels["secret_operation"] = era.secret_action_label

        action_type = st.radio(
            "行动类型",
            options=action_options,
            format_func=lambda x: action_labels.get(x, x),
            key="action_type",
            horizontal=True,
            disabled=event_blocked,
            label_visibility="collapsed",
        )

        command = st.text_area(
            "输入政令",
            value="",
            height=80,
            placeholder=era.secret_action_placeholder,
            key="command_input",
            disabled=event_blocked,
            label_visibility="collapsed",
        )

        if no_key:
            st.warning("⚠️ 未配置 API Key，请在侧边栏「🔑 LLM 驱动引擎配置」中注入密钥后继续。")

        if st.button(era.edict_button, type="primary", use_container_width=True,
                     disabled=event_blocked or not command.strip() or no_key):
            _execute_micro(command, action_type)

        if event_blocked:
            st.warning("⚠️ 有待处理的御前问对，请先做出选择。")

    # ===== 选项卡 2：御前召见 =====
    with tab_audience:
        _render_audience_tab(event_blocked, era)

    # ---- 推进时间（独立大按钮） ----
    st.divider()
    date_str = _current_date_str()
    st.caption(f"📅 当前时间：{date_str}")

    if st.button("⏩ 推进一月", use_container_width=True,
                 disabled=event_blocked or no_key, type="secondary"):
        _execute_advance_month()

    if event_blocked:
        st.warning("⚠️ 请先处理御前问对，再推进时间。")

    # ---- 宏观飞跃区 ----
    with st.expander("🕰️ 宏观国策（时间飞跃）", expanded=False):
        macro_policy = st.text_area(
            "大政方针",
            value="",
            height=60,
            placeholder="例如：休养生息，编练新军，整顿吏治...",
            key="macro_policy_input",
            disabled=event_blocked,
            label_visibility="collapsed",
        )

        col_y1, col_y2, col_y3 = st.columns(3)
        if col_y1.button("⏩⏩ 飞跃 1 年", disabled=event_blocked or not macro_policy.strip() or no_key,
                         use_container_width=True, key="macro_1y"):
            _execute_macro(macro_policy, 1)
        if col_y2.button("⏩⏩ 飞跃 3 年", disabled=event_blocked or not macro_policy.strip() or no_key,
                         use_container_width=True, key="macro_3y"):
            _execute_macro(macro_policy, 3)
        if col_y3.button("⏩⏩ 飞跃 5 年", disabled=event_blocked or not macro_policy.strip() or no_key,
                         use_container_width=True, key="macro_5y"):
            _execute_macro(macro_policy, 5)

        if event_blocked:
            st.caption("⚠️ 请先处理御前问对")

    # ---- 推演结果展示 ----
    last_result = st.session_state.get("last_turn_result")
    if last_result:
        st.divider()
        _render_turn_result(last_result)


# ---------------------------------------------------------------------------
# 御前召见选项卡
# ---------------------------------------------------------------------------

def _render_audience_tab(event_blocked: bool, era) -> None:
    """渲染御前召见选项卡 —— 私密对话 UI。"""
    no_key = not is_api_key_configured()
    audience = st.session_state.get("active_audience")

    # ---- 未开启召见：显示选择器 ----
    if not audience:
        audience_targets = _get_audience_targets(era)
        common_targets = audience_targets + ["其他 (手动宣召)"]
        selected_target = st.selectbox(
            "召见对象",
            options=common_targets,
            key="audience_target",
            disabled=event_blocked or no_key,
        )

        if selected_target == "其他 (手动宣召)":
            actual_target = st.text_input(
                era.audience_placeholder,
                value="",
                key="audience_custom_target",
                disabled=event_blocked or no_key,
            ).strip()
        else:
            actual_target = selected_target

        audience_msg = st.text_area(
            "对话内容",
            value="",
            height=80,
            placeholder="对召见对象说些什么...",
            key="audience_message",
            disabled=event_blocked or no_key,
            label_visibility="collapsed",
        )

        if st.button("👥 宣召入对", type="primary", use_container_width=True,
                     disabled=event_blocked or not audience_msg.strip() or not actual_target or no_key):
            _execute_audience_chat(actual_target, audience_msg)
            st.rerun()

        if event_blocked:
            st.warning("⚠️ 有待处理的御前问对，请先做出选择。")
        return

    # ---- 已开启召见：聊天界面 ----
    target = audience.get("target", "臣僚")
    chat_history = audience.get("chat_history", [])

    # 聊天记录
    for entry in chat_history:
        role = entry.get("role", "user")
        content = entry.get("content", "")
        if role == "user":
            with st.chat_message("user", avatar="👑"):
                st.markdown(f"**朕**：{content}")
        else:
            with st.chat_message("assistant", avatar="🎭"):
                st.markdown(f"**{target}**：{content}")

    # 聊天输入框（st.chat_input 不支持 disabled，用条件渲染替代）
    if not event_blocked and not no_key:
        chat_input = st.chat_input(f"对{target}说……", key="audience_chat_input")
        if chat_input:
            _execute_audience_chat(target, chat_input)
            st.rerun()
    elif no_key:
        st.caption("🔒 需配置 API Key 后方可召对")

    # 结束召见按钮
    col_end, _ = st.columns([1, 2])
    with col_end:
        if st.button("🔴 结束召见 (退朝)", type="secondary", use_container_width=True):
            from src.simulation.audience_turn import end_audience
            end_audience()
            st.session_state.audience_message = ""
            st.rerun()


# ---------------------------------------------------------------------------
# 推演结果渲染
# ---------------------------------------------------------------------------

def _render_turn_result(result: dict) -> None:
    """渲染推演结果（兼容 micro 和 macro 结果）。"""
    if not result.get("ok"):
        st.error(f"推演失败: {result.get('error', '未知错误')}")
        return

    narrative = result.get("narrative", "")
    used_fb = result.get("used_fallback", False)
    years_advanced = result.get("years_advanced", 0)
    is_macro = years_advanced > 0

    if used_fb:
        st.warning("⚠️ LLM 响应格式异常，已启用文本嗅探器兜底。")

    # 对账报告 —— 藏在折叠区，不打断沉浸感
    report = result.get("reconciliation")
    if report and hasattr(report, 'is_clean'):
        if report.is_clean:
            with st.expander("✅ 数值对账通过", expanded=False):
                st.success("LLM 声称值与引擎实际值一致。")
        else:
            with st.expander("⚠️ 底层数值对账报告 (点击查看 LLM 误差)", expanded=False):
                st.error("🔴 **对账异常** —— LLM 声称值与引擎实际值不一致：")
                for d in report.discrepancies:
                    st.caption(f"  • {d}")

    # 叙事文本
    title = f"📜 {'宏观推演' if is_macro else '推演'}叙事"
    with st.expander(title, expanded=True):
        st.markdown(narrative)

    # 效果明细
    effects = result.get("effects", {})
    if effects:
        with st.expander("📊 数值变动明细"):
            for k, v in effects.items():
                sign = "+" if v > 0 else ""
                label = _effect_label(k)
                st.caption(f"  {label} ({k}): {sign}{v}")

    # 宏观跳跃提示
    if is_macro:
        st.info(f"⏱️ 时间已推进 {years_advanced} 年 → 当前：{_current_date_str()}")


# ---------------------------------------------------------------------------
# 执行函数
# ---------------------------------------------------------------------------

def _execute_micro(command: str, action_type: str = "public_edict") -> None:
    if not _ensure_api_key():
        return
    from src.simulation.micro_turn import execute_micro_turn
    with st.spinner("🕰️ 正在推演历史进程……"):
        result = execute_micro_turn(command, action_type)
    st.session_state.last_command = command
    st.session_state.last_action_type = action_type
    st.session_state.last_turn_result = result
    st.rerun()


def _execute_audience_chat(target: str, message: str) -> None:
    if not _ensure_api_key():
        return
    from src.simulation.audience_turn import execute_audience_chat
    with st.spinner(f"🕰️ {target} 正在回话……"):
        execute_audience_chat(target, message)
    # 私密对话结果不记入 last_turn_result（不进编年史）


def _execute_advance_month() -> None:
    if not _ensure_api_key():
        return
    from src.simulation.micro_turn import advance_month_and_tick
    with st.spinner("🕰️ 时光流转……"):
        result = advance_month_and_tick()
    st.session_state.last_command = ""
    st.session_state.last_action_type = "advance_month"
    st.session_state.last_turn_result = result
    st.rerun()


def _execute_macro(policy: str, years: int) -> None:
    if not _ensure_api_key():
        return
    from src.simulation.macro_turn import execute_macro_turn
    with st.spinner(f"🕰️ 正在推演 {years} 年的宏大历史……"):
        result = execute_macro_turn(policy, years)
    st.session_state.last_command = f"[宏指令 {years}年] {policy}"
    st.session_state.last_turn_result = result
    st.rerun()


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _ensure_api_key() -> bool:
    """阻断校验：若未配置 API Key，弹出警告并返回 False。"""
    if not is_api_key_configured():
        st.warning("⚠️ 启动失败：检测到当前圣旨缺乏天机能量（未配置有效的 API Key），请在侧边栏「🔑 LLM 驱动引擎配置」中注入密钥！")
        return False
    return True


def _effect_label(key: str) -> str:
    labels = {
        "treasury": "国库", "manpower": "兵力", "food": "粮草",
        "stability": "民心", "prestige": "威望", "corruption": "腐败度",
    }
    return labels.get(key, key)


def _current_date_str() -> str:
    year = st.session_state.get("year", 0)
    month = st.session_state.get("month", 1)
    if year < 0:
        return f"公元前{abs(year)}年{month}月"
    return f"公元{year}年{month}月"


def _get_audience_targets(era) -> list[str]:
    """从玩家势力军队中提取可召见的将领/大臣列表。"""
    targets: list[str] = []
    player_faction = st.session_state.get("player_faction", "")
    factions = st.session_state.get("factions", {})
    pf = factions.get(player_faction) if player_faction else None

    if pf and hasattr(pf, 'military') and pf.military:
        for u in pf.military:
            if u.general:
                targets.append(u.general)

    # 补充时代人物
    for name in era.default_courtiers:
        if name not in targets:
            targets.append(name)

    return targets if targets else list(era.default_courtiers)
