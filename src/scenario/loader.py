"""
剧本加载器
从 scenarios/scenario_index.json 读取剧本列表（主数据源），
校验后注入 st.session_state。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from src.scenario.schema import validate_scenario
from src.engine.faction import Faction, MilitaryUnit, DiplomacyRelation
from src.engine.gamestate import GameState

# 剧本目录（相对于项目根目录）
SCENARIOS_DIR = Path(__file__).resolve().parent.parent.parent / "scenarios"
_INDEX_PATH = SCENARIOS_DIR / "scenario_index.json"

# 索引缓存（模块级，以 mtime 检测过期）
_index_cache: dict[str, dict[str, Any]] | None = None
_index_mtime: float = 0.0


# ---------------------------------------------------------------------------
# 索引加载（内部）
# ---------------------------------------------------------------------------

def _load_scenario_index() -> dict[str, dict[str, Any]]:
    """
    加载 scenario_index.json，返回 {scenario_id: entry_dict}。
    结果缓存在模块级，通过文件 mtime 自动检测过期。
    """
    global _index_cache, _index_mtime

    if _INDEX_PATH.exists():
        current_mtime = _INDEX_PATH.stat().st_mtime
        if _index_cache is not None and current_mtime == _index_mtime:
            return _index_cache
        _index_mtime = current_mtime
    elif _index_cache is not None:
        return _index_cache

    if not _INDEX_PATH.exists():
        st.warning(f"剧本索引文件缺失: {_INDEX_PATH}，将回退到目录扫描模式。")
        _index_cache = {}
        _index_mtime = 0.0
        return _index_cache

    try:
        data = json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
        entries = data.get("scenarios", [])
        _index_cache = {}
        for entry in entries:
            sid = entry.get("id")
            if sid:
                _index_cache[sid] = entry
        return _index_cache
    except (json.JSONDecodeError, KeyError) as e:
        st.warning(f"剧本索引文件解析失败: {e}，将回退到目录扫描模式。")
        _index_cache = {}
        _index_mtime = 0.0
        return _index_cache


def _reload_index() -> None:
    """强制重新加载索引（用于索引文件更新后）。"""
    global _index_cache, _index_mtime
    _index_cache = None
    _index_mtime = 0.0
    _load_scenario_index()


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def list_scenarios() -> list[dict[str, Any]]:
    """
    返回所有可用剧本的元信息列表（用于剧本选择 UI）。

    优先从 scenario_index.json 读取；若索引缺失则回退到目录扫描。
    """
    index = _load_scenario_index()

    if index:
        # 主路径：从索引文件读取
        results: list[dict[str, Any]] = []
        for sid, entry in sorted(index.items(), key=lambda x: x[1].get("start_year", 0)):
            results.append({
                "id": sid,
                "title": entry.get("title", ""),
                "subtitle": entry.get("subtitle", ""),
                "description": entry.get("description", ""),
                "era": entry.get("era", ""),
                "start_year": entry.get("start_year", 0),
                "tags": entry.get("tags", []),
                "file": entry.get("file", ""),
            })
        return results

    # 回退：目录扫描（索引文件缺失或损坏时）
    return _list_scenarios_fallback()


def _list_scenarios_fallback() -> list[dict[str, Any]]:
    """回退方案：递归扫描 scenarios/ 目录。排除 data/ 和 scenario_index.json。"""
    if not SCENARIOS_DIR.exists():
        return []

    results: list[dict[str, Any]] = []
    for json_path in sorted(SCENARIOS_DIR.glob("**/*.json")):
        if json_path.name == "scenario_index.json":
            continue
        if "data" in json_path.parts:
            continue
        if json_path.name == "scenario_template.json":
            continue
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            meta = data.get("meta", {})
            if not meta.get("id") or not meta.get("title"):
                continue
            results.append({
                "id": meta["id"],
                "title": meta["title"],
                "subtitle": meta.get("subtitle", ""),
                "description": meta.get("description", ""),
                "era": meta.get("era", ""),
                "start_year": meta.get("start_year", 0),
                "tags": meta.get("tags", []),
                "file": json_path.name,
            })
        except (json.JSONDecodeError, KeyError):
            continue

    return results


def load_scenario(scenario_id: str) -> None:
    """
    加载指定剧本，将所有数据注入 st.session_state。
    这是启动游戏的入口函数。

    参数:
        scenario_id: 剧本 ID（如 "chongzhen_1644"），对应 scenarios/<id>.json
    """
    from src.session.manager import deep_cleanup_for_scenario_switch
    from src.map.region_data_loader import reload_map_data

    # 从索引或递归搜索定位文件
    json_path = _find_scenario_file(scenario_id)
    if json_path is None:
        known = sorted(_load_scenario_index().keys()) if _INDEX_PATH.exists() else []
        raise FileNotFoundError(
            f"剧本文件不存在: scenario_id='{scenario_id}'\n"
            f"  搜索目录: {SCENARIOS_DIR}\n"
            f"  索引中已知 ID: {known if known else '(索引为空或缺失)'}\n"
            f"  请检查 scenario_index.json 中是否注册了此剧本，或文件名是否与 ID 匹配。"
        )

    # --- 0. Deep Clean: 清空上一剧本的所有遗留数据 ---
    deep_cleanup_for_scenario_switch()

    # --- 1. 读取 JSON ---
    data = json.loads(json_path.read_text(encoding="utf-8"))

    # --- 2. 校验 ---
    errors = validate_scenario(data)
    if errors:
        error_msg = "\n".join(f"  • {e}" for e in errors)
        raise ValueError(f"剧本校验失败 ({json_path.name}):\n{error_msg}")

    # --- 2.5 加载时代专属地理数据 ---
    map_manifest_key = data.get("meta", {}).get("map_manifest_key", "late_ming_geo")
    reload_map_data(map_manifest_key)

    # --- 2.6 注入 era_metadata 覆盖 ---
    era_metadata = data.get("era_metadata", {})
    if era_metadata:
        _inject_era_metadata_overrides(era_metadata)

    # --- 3. 注入 session_state ---
    st.session_state.era_key = data.get("meta", {}).get("era_key", "ming")
    st.session_state.map_template = data.get("meta", {}).get("map_template", "china")
    st.session_state.world_rules = data.get("meta", {}).get("world_rules", [])
    _inject_meta(data)
    _inject_factions(data)
    _inject_resources(data)
    _inject_military(data)
    _inject_diplomacy(data)
    _inject_territory(data)
    _inject_events(data)
    _inject_butterfly(data)
    _inject_ai_personality(data)
    _inject_gamestate(data)

    # --- 4. 标记加载完成 ---
    st.session_state.scenario_id = scenario_id
    st.session_state.chronicle_log.append({
        "year": data["meta"]["start_year"],
        "month": data.get("meta", {}).get("start_month", 1),
        "season": _month_to_season(data.get("meta", {}).get("start_month", 1)),
        "text": f"【剧本开始】{data['meta']['title']} —— {data['meta'].get('subtitle', '')}",
        "category": "system",
        "importance": 2,
    })


# ---------------------------------------------------------------------------
# 内部注入函数
# ---------------------------------------------------------------------------

def _inject_meta(data: dict) -> None:
    meta = data["meta"]
    st.session_state.scenario_title = meta["title"]
    st.session_state.scenario_meta = meta


def _inject_factions(data: dict) -> None:
    """构造 Faction 对象并注入 session。"""
    factions: dict[str, Faction] = {}
    for fid, fdata in data.get("factions", {}).items():
        factions[fid] = Faction(
            faction_id=fid,
            name=fdata["name"],
            color=fdata["color"],
            ruler=fdata["ruler"],
            ruler_title=fdata.get("ruler_title", ""),
            government=fdata.get("government", ""),
            capital=fdata.get("capital", ""),
            description=fdata.get("description", ""),
            flag_badass=fdata.get("flag_badass", False),
            faction_type=fdata.get("faction_type", "Empire"),
        )
    st.session_state.factions = factions
    st.session_state.player_faction = data.get("player_faction")


def _inject_resources(data: dict) -> None:
    ir = data.get("initial_resources", {})
    st.session_state.resources = {
        fid: dict(res) for fid, res in ir.items()
    }
    # 同时注入到 Faction 对象中
    for fid, res in ir.items():
        faction = st.session_state.factions.get(fid)
        if faction:
            faction.resources = dict(res)


def _inject_military(data: dict) -> None:
    im = data.get("initial_military", {})
    military: dict[str, list[MilitaryUnit]] = {}
    for fid, units in im.items():
        military[fid] = []
        for udata in units:
            military[fid].append(MilitaryUnit(
                name=udata["name"],
                unit_type=udata["type"],
                size=udata["size"],
                location=udata["location"],
                morale=udata["morale"],
                general=udata.get("general", ""),
            ))
        # 注入到 Faction 对象
        faction = st.session_state.factions.get(fid)
        if faction:
            faction.military = military[fid]
    st.session_state.military = military


def _inject_diplomacy(data: dict) -> None:
    relations: list[DiplomacyRelation] = []
    for rdata in data.get("diplomacy", {}).get("relations", []):
        relations.append(DiplomacyRelation(
            faction_a=rdata["a"],
            faction_b=rdata["b"],
            status=rdata["status"],
            tension=rdata["tension"],
        ))
    st.session_state.diplomacy = relations


def _inject_territory(data: dict) -> None:
    ownership = data.get("map", {}).get("initial_ownership", {})
    territory: dict[str, str] = {}
    for fid, regions in ownership.items():
        for region_id in regions:
            territory[region_id] = fid
    st.session_state.territory = territory

    # 注入到 Faction.controlled_regions
    for fid, regions in ownership.items():
        if fid == "neutral":
            continue
        faction = st.session_state.factions.get(fid)
        if faction:
            faction.controlled_regions = list(regions)


def _inject_events(data: dict) -> None:
    st.session_state.scripted_events = data.get("scripted_events", [])
    st.session_state.event_state = "idle"
    st.session_state.active_event = None
    st.session_state.event_queue = []


def _inject_butterfly(data: dict) -> None:
    st.session_state.butterfly_rules = data.get("butterfly_rules", [])
    st.session_state.butterfly_flags = {}


def _inject_ai_personality(data: dict) -> None:
    ap = data.get("ai_personality", {})
    st.session_state.ai_personality = ap
    # 注入到各势力
    for fid, personality in ap.items():
        faction = st.session_state.factions.get(fid)
        if faction:
            faction.aggressiveness = personality.get("aggressiveness", 0.5)
            faction.expansionism = personality.get("expansionism", 0.5)
            faction.diplomacy_preference = personality.get("diplomacy_preference", "neutral")
            faction.decision_weights = personality.get("decision_weights", {})


def _inject_gamestate(data: dict) -> None:
    meta = data["meta"]
    start_year = meta["start_year"]
    start_month = meta.get("start_month", 1)
    st.session_state.year = start_year
    st.session_state.month = start_month
    st.session_state.season = _month_to_season(start_month)
    st.session_state.turn_number = 0


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _month_to_season(month: int) -> str:
    if 1 <= month <= 3:
        return "春"
    elif 4 <= month <= 6:
        return "夏"
    elif 7 <= month <= 9:
        return "秋"
    else:
        return "冬"


def _find_scenario_file(scenario_id: str) -> Path | None:
    """
    查找剧本 JSON 文件。

    优先级：
      1. scenario_index.json 中记录的 file 路径（相对于 SCENARIOS_DIR）
      2. 直接拼接 <scenario_id>.json（根目录）
      3. 递归 glob 搜索（回退，排除 data/ 目录）
    """
    # 1. 主路径：从索引查找
    index = _load_scenario_index()
    if index and scenario_id in index:
        rel_path = index[scenario_id].get("file", "")
        if rel_path:
            full_path = SCENARIOS_DIR / rel_path
            if full_path.exists():
                return full_path
            # 索引中的路径不存在 —— 记录警告并继续回退
            st.warning(f"索引中记录的文件不存在: {rel_path}，尝试回退搜索……")

    # 2. 直接拼接（根目录）
    candidate = SCENARIOS_DIR / f"{scenario_id}.json"
    if candidate.exists():
        return candidate

    # 3. 递归搜索（回退）
    for json_path in sorted(SCENARIOS_DIR.glob("**/*.json")):
        if json_path.name == "scenario_index.json":
            continue
        if "data" in json_path.parts:
            continue
        if json_path.stem == scenario_id:
            return json_path

    # 4. 彻底找不到 —— 打印诊断信息
    _diagnose_missing(scenario_id)
    return None


def _diagnose_missing(scenario_id: str) -> None:
    """打印诊断信息，帮助排查剧本查找失败的问题。"""
    print(f"\n[loader] 查找剧本 '{scenario_id}' 失败。诊断信息：")
    print(f"  SCENARIOS_DIR = {SCENARIOS_DIR}")
    print(f"  SCENARIOS_DIR exists = {SCENARIOS_DIR.exists()}")
    if _INDEX_PATH.exists():
        index = _load_scenario_index()
        print(f"  scenario_index.json: OK ({len(index)} entries)")
        print(f"  Known IDs: {sorted(index.keys())}")
    else:
        print(f"  scenario_index.json: MISSING at {_INDEX_PATH}")
    # 列出所有 JSON 文件
    if SCENARIOS_DIR.exists():
        all_jsons = sorted(SCENARIOS_DIR.glob("**/*.json"))
        print(f"  All JSON files under scenarios/ ({len(all_jsons)}):")
        for p in all_jsons:
            print(f"    {p.relative_to(SCENARIOS_DIR)} (stem={p.stem})")


def _inject_era_metadata_overrides(era_metadata: dict) -> None:
    """
    将 scenario JSON 的 era_metadata 覆盖注入 session_state。

    era_metadata 字段说明：
      - power_center_title: 覆盖侧边栏权力中枢标题
      - intel_org_name:     覆盖情报机构名称
      - region_lore_map:    合并到 current_map_manifest.province_names
    """
    # 权力中枢标题覆盖
    if era_metadata.get("power_center_title"):
        st.session_state.era_power_center_override = era_metadata["power_center_title"]

    # 情报机构名称覆盖
    if era_metadata.get("intel_org_name"):
        st.session_state.era_intel_org_override = era_metadata["intel_org_name"]

    # 区域描述覆盖 —— 合并到 current_map_manifest 中
    region_lore_map = era_metadata.get("region_lore_map", {})
    if region_lore_map:
        manifest = st.session_state.get("current_map_manifest", {})
        province_names = dict(manifest.get("province_names", {}))
        # scenario 级别的 region_lore_map 优先级高于 geography_manifest
        province_names.update(region_lore_map)
        manifest["province_names"] = province_names
        st.session_state.current_map_manifest = manifest
