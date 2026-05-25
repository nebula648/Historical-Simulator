"""
剧本 JSON Schema 定义
用于 jsonschema 校验，确保所有剧本文件结构一致。
"""

from __future__ import annotations

import jsonschema

# ---------------------------------------------------------------------------
# 资源定义（所有剧本必须使用这些 key）
# ---------------------------------------------------------------------------
_RESOURCE_KEYS = ["treasury", "manpower", "food", "stability", "prestige", "corruption"]

# ---------------------------------------------------------------------------
# JSON Schema
# ---------------------------------------------------------------------------

SCENARIO_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["meta", "player_faction", "map", "factions", "initial_resources", "diplomacy"],
    "properties": {
        "meta": {
            "type": "object",
            "required": ["id", "title", "start_year", "time_scale"],
            "properties": {
                "id":            {"type": "string"},
                "title":         {"type": "string"},
                "subtitle":      {"type": "string"},
                "description":   {"type": "string"},
                "era":           {"type": "string"},
                "start_year":    {"type": "integer"},
                "end_year":      {"type": "integer"},
                "time_scale":    {"type": "string", "enum": ["month", "season", "year"]},
                "version":       {"type": "string"},
                "author":        {"type": "string"},
                "tags":          {"type": "array", "items": {"type": "string"}},
                "map_manifest_key": {"type": "string"},
                "era_key":          {"type": "string"},
                "map_template":     {"type": "string", "enum": ["china", "europe"]},
                "world_rules":      {"type": "array", "items": {"type": "string"}},
            },
        },
        "era_metadata": {
            "type": "object",
            "properties": {
                "power_center_title": {"type": "string"},
                "intel_org_name":     {"type": "string"},
                "region_lore_map":    {"type": "object", "additionalProperties": {"type": "string"}},
            },
        },
        "player_faction": {"type": "string"},
        "map": {
            "type": "object",
            "required": ["initial_ownership"],
            "properties": {
                "region_file":       {"type": "string"},
                "initial_ownership": {
                    "type": "object",
                    "additionalProperties": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "factions": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["name", "color", "ruler", "government", "capital"],
                "properties": {
                    "name":              {"type": "string"},
                    "color":             {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"},
                    "ruler":             {"type": "string"},
                    "ruler_title":       {"type": "string"},
                    "government":        {"type": "string"},
                    "capital":           {"type": "string"},
                    "description":       {"type": "string"},
                    "flag_badass":       {"type": "boolean"},
                },
            },
        },
        "initial_resources": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {k: {"type": "integer"} for k in _RESOURCE_KEYS},
                "required": _RESOURCE_KEYS,
            },
        },
        "initial_military": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "type", "size", "location", "morale"],
                    "properties": {
                        "name":     {"type": "string"},
                        "type":     {"type": "string"},
                        "size":     {"type": "integer"},
                        "location": {"type": "string"},
                        "morale":   {"type": "integer", "minimum": 0, "maximum": 100},
                        "general":  {"type": "string"},
                    },
                },
            },
        },
        "diplomacy": {
            "type": "object",
            "required": ["relations"],
            "properties": {
                "relations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["a", "b", "status", "tension"],
                        "properties": {
                            "a":       {"type": "string"},
                            "b":       {"type": "string"},
                            "status":  {"type": "string"},
                            "tension": {"type": "integer", "minimum": 0, "maximum": 100},
                        },
                    },
                },
            },
        },
        "scripted_events": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "name", "type", "trigger", "title", "narrative"],
                "properties": {
                    "id":     {"type": "string"},
                    "name":   {"type": "string"},
                    "type":   {"type": "string", "enum": ["audience", "outcome", "random", "conditional"]},
                    "trigger": {
                        "type": "object",
                        "required": ["condition"],
                        "properties": {
                            "condition": {"type": "string"},
                            "priority":  {"type": "string"},
                        },
                    },
                    "title":           {"type": "string"},
                    "narrative":       {"type": "string"},
                    "choices": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["id", "text", "effects"],
                            "properties": {
                                "id":               {"type": "string"},
                                "text":             {"type": "string"},
                                "effects":          {"type": "object"},
                                "territory_changes": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": ["region_id", "to_faction"],
                                        "properties": {
                                            "region_id":  {"type": "string"},
                                            "to_faction": {"type": "string"},
                                            "reason":     {"type": "string"},
                                        },
                                    },
                                },
                                "narrative_result": {"type": "string"},
                            },
                        },
                    },
                    "auto_effects":        {"type": "object"},
                    "territory_changes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["region_id", "to_faction"],
                            "properties": {
                                "region_id":  {"type": "string"},
                                "to_faction": {"type": "string"},
                                "from_faction": {"type": "string"},
                                "reason":     {"type": "string"},
                            },
                        },
                    },
                    "diplomacy_changes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["a", "b", "tension_delta"],
                            "properties": {
                                "a":             {"type": "string"},
                                "b":             {"type": "string"},
                                "tension_delta": {"type": "integer"},
                                "new_status":    {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
        "butterfly_rules": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "name", "trigger", "delayed_effects"],
                "properties": {
                    "id":   {"type": "string"},
                    "name": {"type": "string"},
                    "trigger": {"type": "string"},
                    "delayed_effects": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["delay_turns", "effect"],
                            "properties": {
                                "delay_turns": {"type": "integer"},
                                "effect":      {"type": "object"},
                                "narrative":   {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
        "ai_personality": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "aggressiveness":       {"type": "number"},
                    "expansionism":         {"type": "number"},
                    "diplomacy_preference": {"type": "string"},
                    "decision_weights":     {"type": "object"},
                },
            },
        },
        "resource_definitions": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["label", "unit", "min", "max"],
                "properties": {
                    "label": {"type": "string"},
                    "unit":  {"type": "string"},
                    "icon":  {"type": "string"},
                    "min":   {"type": "integer"},
                    "max":   {"type": "integer"},
                },
            },
        },
        "victory_conditions": {"type": "object"},
    },
}


def validate_scenario(data: dict) -> list[str]:
    """
    校验剧本 JSON 数据。
    返回错误信息列表，空列表表示校验通过。
    """
    errors: list[str] = []
    try:
        jsonschema.validate(instance=data, schema=SCENARIO_SCHEMA)
    except jsonschema.ValidationError as e:
        errors.append(f"Schema 校验失败: {e.message}")
        return errors

    # --- 业务级校验 ---
    faction_ids = set(data.get("factions", {}).keys())

    # 1. player_faction 必须存在于 factions 中
    pf = data.get("player_faction", "")
    if pf and pf not in faction_ids:
        errors.append(f"player_faction '{pf}' 不在 factions 中")

    # 2. 所有领土归属的 faction 必须存在
    ownership = data.get("map", {}).get("initial_ownership", {})
    for fid, _regions in ownership.items():
        if fid not in faction_ids and fid != "neutral":
            errors.append(f"领土归属中的势力 '{fid}' 不在 factions 中（允许 'neutral'）")

    # 3. initial_resources 的 key 必须与 factions 匹配
    ir = data.get("initial_resources", {})
    for fid in ir:
        if fid not in faction_ids:
            errors.append(f"initial_resources 中的势力 '{fid}' 不在 factions 中")

    # 4. initial_military 的 key 必须与 factions 匹配
    im = data.get("initial_military", {})
    for fid in im:
        if fid not in faction_ids:
            errors.append(f"initial_military 中的势力 '{fid}' 不在 factions 中")

    # 5. 外交关系中的势力必须存在
    for rel in data.get("diplomacy", {}).get("relations", []):
        if rel["a"] not in faction_ids:
            errors.append(f"外交关系中 '{rel['a']}' 不在 factions 中")
        if rel["b"] not in faction_ids:
            errors.append(f"外交关系中 '{rel['b']}' 不在 factions 中")

    # 6. 领土不能有重复归属
    all_regions: list[str] = []
    for _fid, regions in ownership.items():
        all_regions.extend(regions)
    if len(all_regions) != len(set(all_regions)):
        from collections import Counter
        dupes = [r for r, c in Counter(all_regions).items() if c > 1]
        errors.append(f"领土区域重复归属: {dupes}")

    return errors
