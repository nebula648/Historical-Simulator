"""
地理描述数据加载器
从 scenarios/data/geography_manifest.json 加载时代专属地理名称与数据，
支持剧本切换时热重载，彻底隔离不同时代的地理上下文。
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

# 清单文件路径
_MANIFEST_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "scenarios" / "data" / "geography_manifest.json"
)

# 内置硬回退（当清单文件缺失或 key 不存在时使用）
_FALLBACK_MANIFEST: dict = {
    "era_label": "默认",
    "province_names": {},
    "province_base_stats": {},
}

_FALLBACK_BASE_STATS = {"population": 50, "food": 40, "stability": 40}


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def load_geography_manifest() -> dict:
    """
    加载完整的地理清单文件到 session_state.geography_manifest（仅首次或强制刷新时调用）。
    返回整个 manifests 字典。
    """
    if not _MANIFEST_PATH.exists():
        st.warning(f"地理清单文件缺失: {_MANIFEST_PATH}，使用空清单。")
        return {}

    try:
        data = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        manifests = data.get("manifests", {})
        st.session_state.geography_manifest = manifests
        return manifests
    except (json.JSONDecodeError, KeyError) as e:
        st.warning(f"地理清单文件解析失败: {e}，使用空清单。")
        return {}


def reload_map_data(manifest_key: str) -> bool:
    """
    根据剧本指定的 manifest_key 加载时代专属地理数据到 session_state。

    此函数在每次切换剧本时调用，确保 tooltip、区域名称、基础数据
    全部切换为当前时代的版本。

    参数:
        manifest_key: 如 "late_ming_geo", "chu_han_geo", "han_wu_geo", "three_kingdoms_geo"

    返回:
        True 表示加载成功
    """
    # 1. 确保清单已加载
    manifests = st.session_state.get("geography_manifest")
    if not manifests:
        manifests = load_geography_manifest()
        if not manifests:
            st.session_state.current_map_manifest = dict(_FALLBACK_MANIFEST)
            st.session_state.current_map_manifest_key = manifest_key
            return False

    # 2. 加载指定条目
    if manifest_key not in manifests:
        st.warning(
            f"地理清单中不存在 key '{manifest_key}'，"
            f"可用 key: {list(manifests.keys())}。回退到首个可用条目。"
        )
        if manifests:
            manifest_key = next(iter(manifests.keys()))
        else:
            st.session_state.current_map_manifest = dict(_FALLBACK_MANIFEST)
            st.session_state.current_map_manifest_key = manifest_key
            return False

    manifest = manifests[manifest_key]
    st.session_state.current_map_manifest = {
        "era_label": manifest.get("era_label", manifest_key),
        "province_names": dict(manifest.get("province_names", {})),
        "province_base_stats": dict(manifest.get("province_base_stats", {})),
    }
    st.session_state.current_map_manifest_key = manifest_key

    # 3. 记录切换日志
    chronicle = st.session_state.get("chronicle_log", [])
    if chronicle:
        # 只在已有游戏状态时记录（避免启动时的第一次加载也写日志）
        pass  # 由 load_scenario 写日志

    return True


def clear_map_data() -> None:
    """
    彻底清空 session_state 中缓存的所有地理相关数据。
    在剧本切换的 Deep Clean 阶段调用。
    """
    st.session_state.pop("geography_manifest", None)
    st.session_state.pop("current_map_manifest", None)
    st.session_state.pop("current_map_manifest_key", None)


def get_current_province_name(echarts_name: str) -> str:
    """
    获取当前时代下某 Echarts 省份的显示名称。
    未找到时返回原始 echarts_name。
    """
    manifest = st.session_state.get("current_map_manifest")
    if manifest:
        names = manifest.get("province_names", {})
        if echarts_name in names:
            return names[echarts_name]
    return echarts_name


def get_current_province_stats(echarts_name: str) -> dict:
    """
    获取当前时代下某 Echarts 省份的基础统计数据。
    未找到时返回默认值。
    """
    manifest = st.session_state.get("current_map_manifest")
    if manifest:
        stats = manifest.get("province_base_stats", {})
        if echarts_name in stats:
            return dict(stats[echarts_name])
    return dict(_FALLBACK_BASE_STATS)


def get_current_era_label() -> str:
    """获取当前时代的显示标签。"""
    manifest = st.session_state.get("current_map_manifest")
    if manifest:
        return manifest.get("era_label", "未知时代")
    return "未知时代"


def init_geography_if_needed() -> None:
    """
    如果 session_state 中没有地理数据，则加载默认清单。
    在 session/manager.py 的 init_session() 之后调用。
    """
    if "current_map_manifest" not in st.session_state:
        # 尝试回退到 late_ming_geo
        manifests = st.session_state.get("geography_manifest")
        if not manifests:
            manifests = load_geography_manifest()
        if manifests:
            first_key = next(iter(manifests.keys()))
            reload_map_data(first_key)
        else:
            st.session_state.current_map_manifest = dict(_FALLBACK_MANIFEST)
            st.session_state.current_map_manifest_key = "fallback"
