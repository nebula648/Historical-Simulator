"""
全量存档与读档系统
将 st.session_state 核心数据序列化为 JSON，支持多槽位存档。
"""

from __future__ import annotations

import json
from dataclasses import is_dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from src.engine.faction import Faction, MilitaryUnit, DiplomacyRelation

# 存档目录
SAVES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "saves"

# 需要持久化的 session key 白名单
_SAVE_KEYS = [
    "year", "month", "season", "turn_number", "global_flags",
    "scenario_id", "scenario_title", "scenario_meta",
    "player_faction",
    "factions", "resources", "military", "diplomacy", "territory",
    "scripted_events", "event_state", "active_event", "event_queue",
    "butterfly_rules", "butterfly_flags",
    "chronicle_log", "resource_log",
    "ai_personality",
    "sandbox_mode",
]


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def save_game(slot_name: str) -> str:
    """
    保存当前游戏状态到指定槽位。

    参数:
        slot_name: 槽位名称（不含扩展名），如 "auto_1644_turn3"

    返回:
        存档文件的完整路径
    """
    SAVES_DIR.mkdir(parents=True, exist_ok=True)

    save_data: dict[str, Any] = {
        "meta": {
            "slot_name": slot_name,
            "saved_at": datetime.now().isoformat(),
            "scenario_id": st.session_state.get("scenario_id"),
            "scenario_title": st.session_state.get("scenario_title"),
            "year": st.session_state.get("year"),
            "month": st.session_state.get("month"),
            "turn_number": st.session_state.get("turn_number"),
        },
        "game_state": {},
    }

    for key in _SAVE_KEYS:
        value = st.session_state.get(key)
        if value is not None:
            save_data["game_state"][key] = _serialize(value)

    file_path = SAVES_DIR / f"{slot_name}.json"
    file_path.write_text(
        json.dumps(save_data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return str(file_path)


def load_game(slot_name: str) -> bool:
    """
    从指定槽位加载游戏。

    参数:
        slot_name: 槽位名称

    返回:
        True 表示加载成功
    """
    file_path = SAVES_DIR / f"{slot_name}.json"
    if not file_path.exists():
        raise FileNotFoundError(f"存档不存在: {file_path}")

    data = json.loads(file_path.read_text(encoding="utf-8"))
    game_state = data.get("game_state", {})

    # 覆盖 session_state
    for key in _SAVE_KEYS:
        if key in game_state:
            st.session_state[key] = _deserialize(key, game_state[key])

    # 恢复非持久化 key 的默认值
    st.session_state.event_execution_log = st.session_state.get("event_execution_log", [])
    st.session_state.llm_debug_log = st.session_state.get("llm_debug_log", [])
    st.session_state.reconciliation_reports = st.session_state.get("reconciliation_reports", [])
    st.session_state.last_command = ""
    st.session_state.last_turn_result = None
    st.session_state.page = "game_main"

    return True


def list_saves() -> list[dict[str, Any]]:
    """列出所有存档。"""
    SAVES_DIR.mkdir(parents=True, exist_ok=True)
    saves: list[dict[str, Any]] = []
    for f in sorted(SAVES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            meta = data.get("meta", {})
            saves.append({
                "slot_name": f.stem,
                "saved_at": meta.get("saved_at", ""),
                "scenario_title": meta.get("scenario_title", ""),
                "year": meta.get("year", 0),
                "month": meta.get("month", 1),
                "turn_number": meta.get("turn_number", 0),
                "file_size": f.stat().st_size,
            })
        except Exception:
            continue
    return saves


def delete_save(slot_name: str) -> bool:
    """删除指定存档。"""
    file_path = SAVES_DIR / f"{slot_name}.json"
    if file_path.exists():
        file_path.unlink()
        return True
    return False


# ---------------------------------------------------------------------------
# 序列化 / 反序列化
# ---------------------------------------------------------------------------

def _serialize(obj: Any) -> Any:
    """将任意对象序列化为 JSON 兼容类型。"""
    if obj is None:
        return None
    if isinstance(obj, (int, float, str, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(v) for v in obj]
    if is_dataclass(obj):
        return {
            "__dataclass__": obj.__class__.__name__,
            "fields": {k: _serialize(v) for k, v in asdict(obj).items()},
        }
    # Fallback: 尝试 asdict
    if hasattr(obj, "__dict__"):
        return {
            "__class__": obj.__class__.__name__,
            "fields": {k: _serialize(v) for k, v in obj.__dict__.items()},
        }
    return str(obj)


def _deserialize(key: str, data: Any) -> Any:
    """反序列化 JSON 数据回 Python 对象。"""
    if data is None:
        return None
    if isinstance(data, (int, float, str, bool)):
        return data

    if isinstance(data, dict):
        # 检查是否是 dataclass 标记
        cls_name = data.get("__dataclass__") or data.get("__class__")
        fields = data.get("fields", {})

        if cls_name == "Faction":
            return _rebuild_faction(fields)
        elif cls_name == "MilitaryUnit":
            return _rebuild_military_unit(fields)
        elif cls_name == "DiplomacyRelation":
            return _rebuild_diplomacy(fields)
        elif cls_name:
            # 通用 dataclass 重建
            return fields

        # 普通 dict
        return {k: _deserialize(k, v) for k, v in data.items()}

    if isinstance(data, list):
        return [_deserialize("", v) for v in data]

    return data


def _rebuild_faction(fields: dict) -> Faction:
    return Faction(
        faction_id=fields.get("faction_id", ""),
        name=fields.get("name", ""),
        color=fields.get("color", "#888"),
        ruler=fields.get("ruler", ""),
        ruler_title=fields.get("ruler_title", ""),
        government=fields.get("government", ""),
        capital=fields.get("capital", ""),
        description=fields.get("description", ""),
        status=fields.get("status", "active"),
        flag_badass=fields.get("flag_badass", False),
        faction_type=fields.get("faction_type", "Empire"),
        resources=fields.get("resources", {}),
        military=_deserialize("", fields.get("military", [])),
        controlled_regions=fields.get("controlled_regions", []),
        aggressiveness=fields.get("aggressiveness", 0.5),
        expansionism=fields.get("expansionism", 0.5),
        diplomacy_preference=fields.get("diplomacy_preference", "neutral"),
        decision_weights=fields.get("decision_weights", {}),
    )


def _rebuild_military_unit(fields: dict) -> MilitaryUnit:
    return MilitaryUnit(
        name=fields.get("name", ""),
        unit_type=fields.get("unit_type", ""),
        size=fields.get("size", 0),
        location=fields.get("location", ""),
        morale=fields.get("morale", 50),
        general=fields.get("general", ""),
        max_size=fields.get("max_size", 0),
    )


def _rebuild_diplomacy(fields: dict) -> DiplomacyRelation:
    return DiplomacyRelation(
        faction_a=fields.get("faction_a", ""),
        faction_b=fields.get("faction_b", ""),
        status=fields.get("status", "neutral"),
        tension=fields.get("tension", 50),
    )
