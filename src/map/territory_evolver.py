"""
领土动态演化器 —— 接收 territory_changes，更新版图归属
与 Echarts 沙盘无缝桥接，每次变更后前端即时重绘。
"""

from __future__ import annotations

from typing import Any

import streamlit as st


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def apply_territory_changes(changes: list[dict]) -> list[dict]:
    """
    批量应用领土变更，更新 session_state 和势力控制区域。

    参数:
        changes: [
            {"region_id": "da_tong", "to_faction": "shun_regime", "reason": "大顺军攻占大同"},
            ...
        ]

    返回:
        实际应用的变更记录列表（含 from_faction 信息）
    """
    if not changes:
        return []

    territory = st.session_state.get("territory", {})
    factions = st.session_state.get("factions", {})
    applied: list[dict] = []

    for change in changes:
        region_id = change.get("region_id", "")
        to_faction = change.get("to_faction", "")
        reason = change.get("reason", "")

        if not region_id or not to_faction:
            continue

        old_owner = territory.get(region_id, "neutral")

        # 无变化则跳过
        if old_owner == to_faction:
            continue

        # ---- 自动注册未知势力（动态势力生成） ----
        if to_faction != "neutral" and to_faction not in factions:
            new_faction = _auto_register_faction(to_faction, reason)
            if new_faction:
                factions = st.session_state.get("factions", {})
                # 初始化新势力的资源
                resources = st.session_state.get("resources", {})
                if to_faction not in resources:
                    resources[to_faction] = dict(new_faction.resources)
                    st.session_state.resources = resources

        # ---- 更新 territory 映射 ----
        territory[region_id] = to_faction

        # ---- 更新旧势力的 controlled_regions ----
        if old_owner and old_owner != "neutral":
            old_f = factions.get(old_owner)
            if old_f and hasattr(old_f, 'controlled_regions'):
                if region_id in old_f.controlled_regions:
                    old_f.controlled_regions.remove(region_id)

        # ---- 更新新势力的 controlled_regions ----
        if to_faction != "neutral":
            new_f = factions.get(to_faction)
            if new_f and hasattr(new_f, 'controlled_regions'):
                if region_id not in new_f.controlled_regions:
                    new_f.controlled_regions.append(region_id)

        record = {
            "region_id": region_id,
            "from_faction": old_owner,
            "to_faction": to_faction,
            "reason": reason,
            "turn": st.session_state.get("turn_number", 0),
        }
        applied.append(record)

        # ---- 写入编年史 ----
        _log_territory_change(record)

    # ---- 回写 session_state ----
    st.session_state.territory = territory

    return applied


def transfer_region(
    region_id: str,
    to_faction: str,
    reason: str = "",
) -> bool:
    """单项领土转移的便捷函数。"""
    result = apply_territory_changes([{
        "region_id": region_id,
        "to_faction": to_faction,
        "reason": reason,
    }])
    return len(result) > 0


def get_faction_region_count(faction_id: str) -> int:
    """获取某势力当前控制的区域数。"""
    territory = st.session_state.get("territory", {})
    return sum(1 for fid in territory.values() if fid == faction_id)


def get_contested_regions() -> list[dict]:
    """
    检测存在领土争议的区域。
    当前版本使用简化的邻接法：如果某区域与敌对势力的区域邻接，标记为争议。
    后续版本可接入 GeoJSON 邻接矩阵。
    """
    territory = st.session_state.get("territory", {})
    diplomacy = st.session_state.get("diplomacy", [])
    contested: list[dict] = []

    # 构建敌对关系集合
    hostile_pairs: set[tuple[str, str]] = set()
    for rel in diplomacy:
        a = rel.faction_a if hasattr(rel, 'faction_a') else rel.get('faction_a', '')
        b = rel.faction_b if hasattr(rel, 'faction_b') else rel.get('faction_b', '')
        status = rel.status if hasattr(rel, 'status') else rel.get('status', '')
        if status == "war":
            hostile_pairs.add((a, b))
            hostile_pairs.add((b, a))

    if not hostile_pairs:
        return contested

    # 简化：列出所有战区的区域
    for region_id, owner in territory.items():
        if owner == "neutral":
            continue
        # 标记所有处于战争状态的势力所控制的区域为潜在争议
        for (h_a, h_b) in hostile_pairs:
            if owner == h_a:
                contested.append({
                    "region_id": region_id,
                    "owner": owner,
                    "hostile_to": h_b,
                })
                break

    return contested


# ---------------------------------------------------------------------------
# 内部
# ---------------------------------------------------------------------------

def _auto_register_faction(faction_id: str, reason: str = ""):
    """
    动态注册一个不存在于当前势力字典中的新势力。
    优先调用 AI 命名+分类，失败时回退到启发式命名。

    用于处理 LLM 推演中引入的全新势力（外星人、异界、英国舰队等）。
    """
    from src.engine.faction import create_dynamic_faction

    # ---- 1. 尝试 AI 命名 + 类型分类 ----
    ai_name, ai_type = _ai_name_faction(faction_id, reason)

    if ai_name:
        display_name = ai_name
        faction_type = ai_type
    else:
        display_name = _faction_id_to_display_name(faction_id)
        faction_type = _infer_faction_type(faction_id)

    # ---- 2. 创建势力 ----
    new_faction = create_dynamic_faction(faction_id, display_name, faction_type)
    factions = st.session_state.get("factions", {})
    factions[faction_id] = new_faction
    st.session_state.factions = factions

    # ---- 3. 编年史记录 ----
    from src.engine.faction import FACTION_TYPE_TRAITS
    traits = FACTION_TYPE_TRAITS.get(faction_type, {})
    type_label = traits.get("label", "未知")
    naming_source = "AI 命名" if ai_name else "启发式命名"

    entry = {
        "year": st.session_state.get("year", 0),
        "month": st.session_state.get("month", 1),
        "season": st.session_state.get("season", ""),
        "text": (
            f"<span style='color:#9932CC;font-weight:bold;'>"
            f"【🌍 新势力登场】{display_name}（{faction_id}）首次出现于历史舞台！"
            f"类型：{type_label} · 势力色：{new_faction.color} · {naming_source}</span>"
        ),
        "category": "system",
        "importance": 3,
    }
    chronicle = st.session_state.get("chronicle_log", [])
    chronicle.append(entry)
    st.session_state.chronicle_log = chronicle

    return new_faction


def _ai_name_faction(faction_id: str, reason: str = "") -> tuple[str, str]:
    """
    调用轻量级 LLM 为新势力生成中文名和类型分类。

    返回:
        (display_name, faction_type) — 失败时返回 ("", "")
    """
    try:
        from src.llm.client import generate_response
        from src.llm.prompt_builder import (
            FACTION_NAMING_SYSTEM_PROMPT,
            build_faction_naming_prompt,
        )
        from src.llm.json_extractor import extract_json

        description = reason if reason else f"势力ID为 {faction_id}，由推演引擎动态生成。"
        user_prompt = build_faction_naming_prompt(faction_id, description)
        raw = generate_response(user_prompt, FACTION_NAMING_SYSTEM_PROMPT)
        data = extract_json(raw)

        name = data.get("name", "").strip()
        ftype = data.get("type", "Empire").strip()

        # 验证类型是否合法
        from src.engine.faction import FACTION_TYPE_TRAITS
        if ftype not in FACTION_TYPE_TRAITS:
            ftype = "Empire"

        if name:
            return name, ftype
    except Exception:
        pass

    return "", ""


def _infer_faction_type(faction_id: str) -> str:
    """根据 faction_id 中的关键词推断势力类型。"""
    fid_lower = faction_id.lower()
    # 丧尸/亡灵/病毒
    if any(kw in fid_lower for kw in ("zombie", "undead", "virus", "plague", "horde", "dead", "ghoul", "corpse")):
        return "ZombieHorde"
    # 外星/异星
    if any(kw in fid_lower for kw in ("alien", "space", "cosmic", "star", "mars", "ufo", "extraterrestrial")):
        return "Alien"
    # 修仙/魔法/宗门
    if any(kw in fid_lower for kw in ("xiuxian", "cult", "sect", "magic", "sorcery", "wizard", "dao", "immortal", "demon", "spirit")):
        return "Cult"
    # 游牧/部落
    if any(kw in fid_lower for kw in ("horde", "nomad", "steppe", "mongol", "tribe", "clan", "tribal")):
        return "Horde"
    # 起义/叛乱
    if any(kw in fid_lower for kw in ("rebel", "revolt", "uprising", "peasant", "insurgent")):
        return "Rebel"
    # 王国
    if any(kw in fid_lower for kw in ("kingdom", "king", "royal", "monarchy")):
        return "Kingdom"
    # 部落
    if any(kw in fid_lower for kw in ("tribe", "tribal")):
        return "Tribe"
    # 默认帝国
    return "Empire"


def _faction_id_to_display_name(faction_id: str) -> str:
    """将 faction_id 转换为人类可读的显示名（启发式回退）。"""
    # 常见 ID 映射
    known_names = {
        "british_empire": "大英帝国远征舰队",
        "alien_invaders": "天外异星舰队",
        "xiuxian_sect": "修仙宗门联盟",
        "demon_army": "域外天魔军",
        "atlantis": "亚特兰蒂斯帝国",
        "robot_army": "机械军团",
        "undead_horde": "亡灵天灾军团",
        "mongol_remnant": "蒙古残部",
        "japanese_shogunate": "日本幕府远征军",
        "french_empire": "法兰西帝国远征军",
        "portuguese_empire": "葡萄牙远东舰队",
        "dutch_empire": "荷兰东印度公司",
        "spanish_empire": "西班牙无敌舰队",
        "russian_empire": "沙俄远征军",
        "zombie_virus": "天启丧尸军团",
        "zombie_horde": "尸潮狂潮",
        "infected_zone": "感染区",
        "undead_army": "不死军团",
        "plague_bearers": "疫病使者",
        "alien_fleet": "深空异星舰队",
        "cosmic_horror": "宇宙恐怖",
        "elf_kingdom": "精灵王国",
        "dwarf_kingdom": "矮人王国",
        "orc_horde": "兽人部落",
        "vampire_coven": "血族议会",
        "werewolf_pack": "狼人部族",
        "sky_cult": "天穹教",
        "shadow_guild": "暗影公会",
        "pirate_confederation": "海盗同盟",
        "merchant_republic": "商业共和国",
        "theocratic_state": "神权国",
    }
    if faction_id in known_names:
        return known_names[faction_id]

    # 关键词模式匹配
    fid_lower = faction_id.lower()
    if "zombie" in fid_lower or "undead" in fid_lower or "virus" in fid_lower:
        return f"丧尸军团·{faction_id.replace('_', ' ').title()}"
    if "alien" in fid_lower or "space" in fid_lower:
        return f"异星势力·{faction_id.replace('_', ' ').title()}"
    if "cult" in fid_lower or "sect" in fid_lower or "magic" in fid_lower:
        return f"神秘宗门·{faction_id.replace('_', ' ').title()}"
    if "horde" in fid_lower or "nomad" in fid_lower:
        return f"游牧部族·{faction_id.replace('_', ' ').title()}"
    if "rebel" in fid_lower or "revolt" in fid_lower:
        return f"义军·{faction_id.replace('_', ' ').title()}"

    # 通用转换: "british_empire" → "British Empire"
    return faction_id.replace("_", " ").title()


def _log_territory_change(record: dict) -> None:
    """将领土变更记录写入编年史（使用当前时代的区域名称）。"""
    from src.map.region_data_loader import get_current_province_name

    region_id = record["region_id"]
    old = record.get("from_faction", "neutral")
    new = record["to_faction"]
    reason = record.get("reason", "")
    reason_text = f"（{reason}）" if reason else ""

    factions = st.session_state.get("factions", {})
    old_name = factions[old].name if old in factions else "无主之地"
    new_name = factions[new].name if new in factions else "无主之地"

    # 使用当前时代的区域显示名称
    era_region = get_current_province_name(region_id)
    display_region = f"{era_region}（{region_id}）" if era_region != region_id else region_id

    entry = {
        "year": st.session_state.get("year", 0),
        "month": st.session_state.get("month", 1),
        "season": st.session_state.get("season", ""),
        "text": f"【版图变更】{display_region}：{old_name} → {new_name}{reason_text}",
        "category": "military",
        "importance": 1,
    }
    chronicle = st.session_state.get("chronicle_log", [])
    chronicle.append(entry)
    st.session_state.chronicle_log = chronicle
