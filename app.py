"""
历史模拟器 —— 入口文件
职责：页面路由 + Session 初始化 + API Key 注入面板，不含业务逻辑。
"""

import streamlit as st

# ---------------------------------------------------------------------------
# 页面配置（必须是第一个 st. 调用）
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="历史模拟器",
    page_icon="🏯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# 延迟导入（加速冷启动，避免循环依赖）
# ---------------------------------------------------------------------------
from src.session.manager import init_session

# ---------------------------------------------------------------------------
# 路由常量
# ---------------------------------------------------------------------------
PAGE_SCENARIO_PICKER = "scenario_picker"
PAGE_GAME_MAIN = "game_main"


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> None:
    init_session()
    _render_api_key_panel()
    _ensure_api_key_warning()

    page = st.session_state.get("page", PAGE_SCENARIO_PICKER)

    if page == PAGE_SCENARIO_PICKER:
        _render_scenario_picker()
    elif page == PAGE_GAME_MAIN:
        _render_game_main()
    else:
        st.error(f"未知页面: {page}")
        st.session_state.page = PAGE_SCENARIO_PICKER
        st.rerun()


# ---------------------------------------------------------------------------
# API Key 注入面板 —— 侧边栏最上方，所有页面可见
# ---------------------------------------------------------------------------
def _render_api_key_panel() -> None:
    """在侧边栏顶部渲染 LLM 引擎配置面板。"""
    if "user_api_key" not in st.session_state:
        st.session_state.user_api_key = ""
    if "api_vendor" not in st.session_state:
        st.session_state.api_vendor = "DeepSeek"
    if "custom_api_base" not in st.session_state:
        st.session_state.custom_api_base = ""
    if "custom_api_model" not in st.session_state:
        st.session_state.custom_api_model = ""

    with st.sidebar:
        with st.expander(
            "🔑 LLM 驱动引擎配置 (使用前请先配置 API Key)",
            expanded=st.session_state.user_api_key == "",
        ):
            vendor_label = st.selectbox(
                "选择模型供应商",
                ["DeepSeek", "Anthropic (Claude)", "OpenAI", "自定义中转站"],
                key="api_vendor",
            )

            temp_key = st.text_input(
                "请输入您的 API Key:",
                value=st.session_state.user_api_key,
                type="password",
                placeholder="sk-...",
                key="api_key_input",
            )
            if temp_key != st.session_state.user_api_key:
                st.session_state.user_api_key = temp_key

            if st.session_state.api_vendor == "自定义中转站":
                custom_url = st.text_input(
                    "中转站 Base URL:",
                    value=st.session_state.custom_api_base,
                    placeholder="https://your-endpoint.com/v1",
                    key="custom_api_base_input",
                )
                if custom_url != st.session_state.custom_api_base:
                    st.session_state.custom_api_base = custom_url

                custom_model = st.text_input(
                    "模型名称:",
                    value=st.session_state.custom_api_model,
                    placeholder="gpt-4o / claude-sonnet-4-6",
                    key="custom_api_model_input",
                )
                if custom_model != st.session_state.custom_api_model:
                    st.session_state.custom_api_model = custom_model

            st.caption("您的 Key 仅保存在当前浏览器会话中，不会上传至任何服务器。")

        if st.session_state.user_api_key:
            vendor_short = st.session_state.api_vendor.split(" ")[0]
            st.success(f"✅ {vendor_short} Key 已就绪")


def _ensure_api_key_warning() -> None:
    """若未配置 API Key，在侧边栏底部显示醒目警告。"""
    if not st.session_state.get("user_api_key"):
        with st.sidebar:
            st.warning("⚠️ 未配置 API Key，游戏功能受限")


# ---------------------------------------------------------------------------
# 剧本选择页 —— 委托给 src/ui/scenario_picker.py
# ---------------------------------------------------------------------------
def _render_scenario_picker() -> None:
    from src.ui.scenario_picker import render
    render()


# ---------------------------------------------------------------------------
# 游戏主页面 —— 委托给 src/ui/layout.py
# ---------------------------------------------------------------------------
def _render_game_main() -> None:
    from src.ui.layout import render_game_main

    # 边栏底部：返回按钮 + 调试开关
    with st.sidebar:
        st.divider()
        if st.button("↩ 返回剧本选择", use_container_width=True):
            st.session_state.page = PAGE_SCENARIO_PICKER
            st.rerun()

        debug_mode = st.session_state.get("debug_mode", False)
        if st.checkbox("🔧 天机阁（调试模式）", value=debug_mode):
            st.session_state.debug_mode = True
            st.info("天机阁将在后续版本中实现。")
        else:
            st.session_state.debug_mode = False

    render_game_main()


# ---------------------------------------------------------------------------
# 启动
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
