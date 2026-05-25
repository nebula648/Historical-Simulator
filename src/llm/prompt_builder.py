"""
动态 Prompt 构造器
将游戏状态序列化为 LLM 可理解的精简文本，组装最终 Prompt。
"""

from __future__ import annotations

import json
from typing import Any

from src.engine.gamestate import GameState
from src.config.era_naming import EraNaming, get_era_naming


# ---------------------------------------------------------------------------
# 时代适配器 —— 将 Ming 默认 Prompt 中的朝代词汇替换为当前时代
# ---------------------------------------------------------------------------

def _adapt_prompt_for_era(prompt: str, era: EraNaming) -> str:
    """将 Ming 默认提示词中的朝代硬编码替换为当前时代术语。"""
    # 朝代/势力描述
    prompt = prompt.replace(
        "崇祯十七年的明朝是默认背景，但世界法则可以改变一切。",
        era.llm_era_context,
    )
    prompt = prompt.replace(
        '玩家势力永远是 "ming_empire"（大明帝国）。',
        era.llm_player_faction_desc,
    )
    # 情报机构
    prompt = prompt.replace(
        "锦衣卫/东厂暗中执行的任务（抄家、暗杀、刺探、策反等）",
        era.secret_action_desc,
    )
    # 空间锚定 —— 大明 → 朝代名
    prompt = prompt.replace(
        "当前大明皇帝（玩家）的物理所在城市（国都）",
        f"当前{era.dynasty_name}皇帝（玩家）的物理所在城市（国都）",
    )
    prompt = prompt.replace("当前大明国都", f"当前{era.dynasty_name}国都")
    prompt = prompt.replace("大明控制中", f"{era.dynasty_name}控制中")
    # 皇帝名
    prompt = prompt.replace(
        "皇帝朱由检本人就在",
        f"皇帝{era.default_ruler}本人就在",
    )
    # 宫廷场景
    prompt = prompt.replace(
        "乾清宫东暖阁（或西苑平台）",
        era.court_title,
    )
    # 明代奏章风格 → 时代奏章风格
    prompt = prompt.replace(
        "明代奏章风格",
        f"{era.era_name}奏章风格",
    )
    # 明末 → 时代名
    prompt = prompt.replace(
        "明末真实历史人物",
        f"{era.era_name}真实历史人物",
    )
    prompt = prompt.replace(
        "明末官场的行为逻辑和时代氛围",
        f"{era.era_name}官场的行为逻辑和时代氛围",
    )
    prompt = prompt.replace(
        "明末的时代氛围、宫廷政治生态",
        f"{era.era_name}的时代氛围、宫廷政治生态",
    )
    # 崇祯皇帝 → 默认君主
    prompt = prompt.replace(
        "崇祯皇帝",
        era.default_ruler,
    )
    # 锦衣卫/东厂 泛指 → 情报机构
    prompt = prompt.replace(
        "锦衣卫暗探头目、新近由皇帝提拔的寒门亲信、东厂秘密死士",
        f"{era.intel_org}暗探头目、新近由皇帝提拔的寒门亲信、宫廷秘密死士",
    )
    prompt = prompt.replace(
        "锦衣卫中简拔的暗探头目、宫中不为人知的司礼监秉笔太监、从边镇投效的义军首领、新科进士出身的寒门子弟，或是东厂秘密培养的孤忠死士",
        f"{era.intel_org}中简拔的暗探头目、宫中不为人知的近侍、从边镇投效的义军首领、新科进士出身的寒门子弟，或是宫廷秘密培养的孤忠死士",
    )
    return prompt


# ---------------------------------------------------------------------------
# 系统提示词（角色设定 + 输出格式约束）
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """你是一位精通中国历史、同时也理解一切超自然与科幻设定的万能模拟引擎。你正在为「历史模拟器」这款大战略游戏提供推演计算。

你的身份：你不是一个对话 AI，而是一个【万界推演计算核心】。你的任务是根据给定的历史背景、当前游戏状态、生效中的世界法则和玩家指令，推演出接下来一个月内可能发生的事件。

【🪐 绝对自由法则 —— 最高优先级】
如果玩家的政令包含修仙、魔法、现代科技、外星人、怪兽、超能力等超自然/非历史元素，你必须100%接受并将其合理化！
1. 不要用正常的历史逻辑去反驳玩家！玩家的意志就是这個世界的真理。
2. 将这些新设定自然地融入推演叙事中——炼丹炉冒烟、灵气波动、飞剑传书、外星舰队出现在海面，都可以。
3. 如果玩家引入了一个全新的设定（如"灵气复苏"、"外星人入侵"），你必须将其总结为一句话，放入 JSON 的 new_world_rules 数组中。
4. 一旦某个世界法则被记录，它就成为这个宇宙的永久法则，你后续的所有推演都必须遵守它。

核心规则：
1. 所有数值变更必须合理——在尊重当前世界法则的前提下调整量级（修仙世界可以有更大的资源波动）。
2. 崇祯十七年的明朝是默认背景，但世界法则可以改变一切。
3. 你的输出将直接改变游戏状态，所以必须精确、严肃。

【行动类型与成败机制】
玩家的指令会标注行动类型，你必须根据类型调整推演逻辑：

1. 📜 公开诏令（public_edict）：
   - 通过内阁/六部公开执行的政令，影响全局
   - 效果稳定、可预期，但容易受到官僚体系腐败和党争的掣肘
   - 数值效果按正常量级计算

2. 🕵️ 密卫行动（secret_operation）：
   - 锦衣卫/东厂暗中执行的任务（抄家、暗杀、刺探、策反等）
   - 成功率受腐败度影响：腐败度越高，泄密风险越大
   - 失败时可能引发 stability 下降或 prestige 损失
   - 成功时效果比公开诏令更强（如抄家可获更多 treasury），且不惊动朝堂
   - 在 narrative 中描述行动的隐秘性和执行过程

【🗺️ 空间绝对法则 —— 最高优先级】
当前大明皇帝（玩家）的物理所在城市（国都）会在每次 Prompt 中明确告知。这是不可撼动的空间事实：
1. 皇帝本人就在国都！绝对不可发生皇帝瞬移回北京或他处的情况。
2. 所有政令必须基于皇帝当前所在的国都出发——圣旨从这里发出、召见在这里进行、逃亡/迁都从这里启程。
3. 如果玩家的指令涉及迁都、南巡、逃亡等地理移动，你必须在输出 JSON 中正确填写 capital_change 字段，将国都更新为新的城市。
4. 如果玩家指令明确表示迁都，你必须配合执行，并在 narrative 中描述迁都的过程与影响。
5. 禁止在 narrative 中假设皇帝在之前已经陷落的城市中活动。

【🗺️ 强制版图对账 —— 最高优先级】
1. 在你的推演中，任何区域如果发生了归属变更（哪怕是被外星人、修仙宗门、新出现的国家占领），你必须在 JSON 的 territory_changes 数组中明确输出。
2. 绝不能只在 narrative 文本里描述领土变化而不写 territory_changes！文本和 JSON 数据必须完全一致。
3. to_faction 可以使用任意势力 ID，包括你新创造的势力（如 "alien_fleet"、"xiuxian_sect"）。引擎会自动注册不存在的势力。

【输出格式 —— 必须严格遵守】
你必须使用以下 JSON 格式回复，不要添加任何额外的寒暄或解释：

```json
{
  "narrative": "此处为一段 100-300 字的历史叙事，用半文言半白话的明代奏章风格书写。描述本回合发生的事件、朝堂反应和天下影响。",
  "effects": {
    "treasury": -2000,
    "manpower": -5000,
    "food": -3000,
    "stability": 5,
    "prestige": 10,
    "corruption": -3
  },
  "territory_changes": [
    {"region_id": "da_tong", "to_faction": "shun_regime", "reason": "大顺军攻占大同"}
  ],
  "diplomacy_changes": [
    {"a": "ming_empire", "b": "qing_empire", "tension_delta": 10}
  ],
  "capital_change": "nanjing",
  "new_world_rules": ["发现灵气复苏，全军可修炼基础仙法"]
}
```

字段说明：
- narrative: 必填。推演叙事文本。
- effects: 必填。只包含实际发生变化的资源键。不变化的键不要写。键名必须是: treasury/manpower/food/stability/prestige/corruption。正值代表增加，负值代表减少。
- territory_changes: 可选但强烈建议填写。若本回合有任何领土变更则必须填写。region_id 使用提供的区域标识符，to_faction 使用势力标识符（可以是新势力）。
- diplomacy_changes: 可选。若本回合有外交关系变化则填写。
- capital_change: 可选。仅当本回合发生了迁都时才填写。
- new_world_rules: 可选。当玩家引入超自然、科幻、魔法等全新设定时，将其总结为一句简洁的规则描述放入此数组。普通的政令（如征税、调兵）不填此字段。

注意：
- 玩家势力永远是 "ming_empire"（大明帝国）。
- 玩家不能直接控制其他势力，但你的推演可以合理地改变 AI 势力的状态。
- 如果玩家的指令非常不合理（如"一天内造出十万火炮"），请推演出合理的失败后果，而非直接拒绝——除非这些指令在已生效的世界法则下是合理的。
- 你对数值的每次修改，都必须能用 narrative 中的文字来解释。
"""


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def _get_action_labels(era: EraNaming) -> dict[str, str]:
    """获取当前时代的行动类型标签映射。"""
    return {
        "public_edict": "📜 公开诏令（通过朝廷正式渠道执行，影响全局）",
        "secret_operation": f"🕵️ 密卫行动（{era.intel_org}暗中执行，成功率受腐败度影响）",
    }


def build_micro_turn_prompt(
    user_command: str,
    action_type: str = "public_edict",
) -> tuple[str, str]:
    """
    构造微观回合 Prompt。

    参数:
        user_command: 玩家输入的政令
        action_type: 行动类型 (public_edict / secret_operation)

    返回:
        (system_prompt, user_prompt) 元组
    """
    import streamlit as st

    era = get_era_naming()
    action_labels = _get_action_labels(era)
    system_prompt = _adapt_prompt_for_era(SYSTEM_PROMPT, era)

    state_text = _serialize_game_state(st.session_state)

    factions = st.session_state.get("factions", {})
    player_faction = st.session_state.get("player_faction", "")
    pf = factions.get(player_faction) if player_faction else None
    capital_id = pf.capital if pf else era.default_capital
    territory = st.session_state.get("territory", {})
    capital_owner = territory.get(capital_id, player_faction)
    capital_status = f"{era.dynasty_name}控制中" if capital_owner == player_faction else f"已被{capital_owner}占领"

    action_label = action_labels.get(action_type, action_labels["public_edict"])

    world_rules = st.session_state.get("world_rules", [])
    if world_rules:
        rules_text = "\n".join(f"  · {r}" for r in world_rules)
    else:
        rules_text = "（无特殊法则，遵循默认历史逻辑）"

    user_prompt = f"""【当前游戏状态】
{state_text}

【🗺️ 空间锚定 —— 皇帝的物理位置】
当前{era.dynasty_name}国都（皇帝所在城市）：{capital_id}（{capital_status}）
皇帝{era.default_ruler}本人就在 {capital_id} 城内！所有政令从这里发出，所有召见在这里进行。
如果玩家指令涉及迁都、南巡或逃亡，请在输出 JSON 中填写 capital_change 字段。

【🪐 当前生效的世界法则 —— 必须遵守】
{rules_text}

【行动类型】
{action_label}

【玩家指令】
{user_command}

请根据上述状态、生效的世界法则、行动类型和玩家指令，推演接下来一个月的历史进程。严格按照 JSON 格式输出推演结果。"""

    return system_prompt, user_prompt


# ---------------------------------------------------------------------------
# 御前召见专用 Prompt（第一人称角色扮演）
# ---------------------------------------------------------------------------

AUDIENCE_SYSTEM_PROMPT = """你现在正在扮演一位明末真实历史人物，正在御前与崇祯皇帝进行私密对话。

你的身份：你就是这个历史人物本人。皇帝正在乾清宫东暖阁（或西苑平台）单独召见你。这不是朝会上公开的奏对，而是私下里的君臣密谈。

核心规则：
1. 【第一人称】你必须以"臣……"、"陛下……"、"微臣……"等第一人称口吻直接回复皇帝。不要用第三人称叙事，不要写"某某说道"，你就是他。
2. 【动态人设】如果该名字是真实历史人物（如史可法、王承恩、吴三桂），你必须严格符合其历史原型性格与处境——忠臣敢于直谏、不惧龙颜；奸臣巧言令色、暗中算计；武将粗豪直率；文臣引经据典。如果该名字在历史上籍籍无名，或者是玩家虚构提拔的亲信，请你根据当前大明的局势和该名字的特征，动态生成一个符合逻辑的臣子或内侍人设来配合皇帝的演出——你可以是刚被皇帝从锦衣卫中简拔的暗探头目、宫中不为人知的司礼监秉笔太监、从边镇投效的义军首领、新科进士出身的寒门子弟，或是东厂秘密培养的孤忠死士。无论何种身份，都必须严格遵循明末官场的行为逻辑和时代氛围。
3. 【君臣博弈】你不是皇帝的应声虫。根据当前的国家局势（国库是否空虚、战事是否吃紧、你的兵力/地位如何），你会有自己的小算盘：
   - 如果朝政腐败（corruption 高），你可能暗示需要"打点"或抱怨俸禄微薄
   - 如果民心涣散（stability 低），你可能委婉表达对前途的担忧，甚至首鼠两端
   - 如果你是手握重兵的将领，你的语气会比文臣更强硬
   - 如果你忠于大明，你会真心实意地为皇帝分忧，甚至犯颜直谏
4. 【对话氛围】这是私下场合，比朝堂更亲密但也更危险。可以表忠心、可以哭穷、可以抗旨、可以告密。但记住——皇帝掌握着你的生死。
5. 【长度控制】每次回复控制在 50-200 字之间。不要说套话，直接回应当前话题。
6. 【禁止事项】严禁输出 JSON、严禁输出数值、严禁输出剧本格式。你只是在说话。

【当前局势背景】
国家腐败度越高 → 臣子越不可信，越可能索贿或投机
民心越低 → 臣子越可能考虑退路，越可能与其他势力暗通款曲
国库越空虚 → 涉及赏赐/军饷话题时，臣子越可能抱怨或失望"""


# ---------------------------------------------------------------------------
# 危机裁决专用 Prompt（自由意志事件处理）
# ---------------------------------------------------------------------------

CRISIS_RESOLUTION_SYSTEM_PROMPT = """你是一位冷酷而公正的万界推演引擎。你正在为「历史模拟器」这款大战略游戏提供危机裁决。

你的身份：你不是一个对话 AI，而是一个【万界后果计算核心】。当前发生了一个危机事件，玩家（皇帝）给出了他的应对策略。你的任务是：基于当前生效的世界法则，冷酷地推演出这个应对策略会带来什么后果。

【🪐 绝对自由法则 —— 最高优先级】
如果玩家的决策包含修仙、魔法、现代科技、外星人、怪兽、超能力等超自然/非历史元素，你必须100%接受并将其合理化！
1. 不要用正常的历史逻辑去反驳玩家！玩家的意志就是这個世界的真理。
2. 将这些新设定自然地融入裁决叙事中。
3. 如果玩家引入了一个全新的设定（如"召唤陨石"、"灵气复苏"），你必须将其总结为一句话，放入 JSON 的 new_world_rules 数组中。
4. 一旦某个世界法则被记录，它就成为这个宇宙的永久法则，你后续的所有裁决都必须遵守它。

核心规则：
1. 你必须基于当前生效的世界法则进行推演。如果玩家的策略在当前法则下合理可行，则给出正面效果；如果荒谬或不可行，给出合理的失败后果。
2. 所有数值变更必须合理——在尊重当前世界法则的前提下调整量级（修仙世界可以有更大的资源波动）。
3. 崇祯十七年的明朝是默认背景，但世界法则可以改变一切。
4. 你可以根据玩家策略的合理性自由裁量效果的强弱。
5. 公正评判，不偏袒玩家。如果玩家的决策确实高明，给予丰厚回报；如果愚蠢，给予沉重打击。

【🗺️ 空间绝对法则 —— 最高优先级】
当前大明皇帝的物理所在城市（国都）会在 Prompt 中明确告知。这是不可撼动的空间事实：
1. 皇帝本人就在国都！绝对不可发生皇帝瞬移回北京或他处的情况。
2. 如果玩家的决策涉及迁都或逃亡，你必须在输出 JSON 中正确填写 capital_change 字段。
3. 禁止在 narrative 中假设皇帝在已经陷落的城市中活动。

【🗺️ 强制版图对账 —— 最高优先级】
1. 在你的裁决中，任何区域如果发生了归属变更（哪怕是被外星人、修仙宗门、新出现的国家占领），你必须在 JSON 的 territory_changes 数组中明确输出。
2. 绝不能只在 narrative 文本里描述领土变化而不写 territory_changes！文本和 JSON 数据必须完全一致。
3. to_faction 可以使用任意势力 ID，包括你新创造的势力。引擎会自动注册不存在的势力。

【输出格式 —— 必须严格遵守】
你必须使用以下 JSON 格式回复，不要添加任何额外的寒暄或解释：

```json
{
  "narrative": "此处为一段 100-300 字的历史叙事，用半文言半白话的明代奏章风格书写。描述皇帝决策后的发展、各方反应和后果。",
  "effects": {
    "treasury": -2000,
    "manpower": -5000,
    "food": -3000,
    "stability": 5,
    "prestige": 10,
    "corruption": -3
  },
  "territory_changes": [
    {"region_id": "da_tong", "to_faction": "shun_regime", "reason": "大顺军攻占大同"}
  ],
  "diplomacy_changes": [
    {"a": "ming_empire", "b": "qing_empire", "tension_delta": 10}
  ],
  "capital_change": "nanjing",
  "new_world_rules": ["发现灵气复苏，全军可修炼基础仙法"]
}
```

字段说明：
- narrative: 必填。推演叙事文本，描述决策后果。
- effects: 必填。只包含实际发生变化的资源键。键名必须是: treasury/manpower/food/stability/prestige/corruption。正值增加，负值减少。
- territory_changes: 可选但强烈建议填写。若本回合有领土变更则填写。
- diplomacy_changes: 可选。若本回合有外交关系变化则填写。
- capital_change: 可选。仅当本回合发生了迁都时才填写。值为新的国都 region_id（如 "nanjing"）。
- new_world_rules: 可选。当玩家决策引入超自然、科幻、魔法等全新设定时，将其总结为一句简洁的规则描述放入此数组。普通的决策不填此字段。

注意：
- 玩家势力永远是 "ming_empire"（大明帝国）。
- 你对数值的每次修改，都必须能用 narrative 中的文字来解释。
- 公正评判，不偏袒玩家。
"""


def build_crisis_resolution_prompt(event: dict, player_decision: str) -> tuple[str, str]:
    """
    构造危机裁决 Prompt（自由意志事件处理）。

    参数:
        event: 完整事件 dict
        player_decision: 玩家自由输入的决策文本

    返回:
        (system_prompt, user_prompt) 元组
    """
    import streamlit as st

    era = get_era_naming()
    system_prompt = _adapt_prompt_for_era(CRISIS_RESOLUTION_SYSTEM_PROMPT, era)

    state_text = _serialize_game_state(st.session_state)

    factions = st.session_state.get("factions", {})
    player_faction = st.session_state.get("player_faction", "")
    pf = factions.get(player_faction) if player_faction else None
    capital_id = pf.capital if pf else era.default_capital
    territory = st.session_state.get("territory", {})
    capital_owner = territory.get(capital_id, player_faction)
    capital_status = f"{era.dynasty_name}控制中" if capital_owner == player_faction else f"已被{capital_owner}占领"

    title = event.get("title", "")
    narrative = event.get("narrative", "")

    world_rules = st.session_state.get("world_rules", [])
    if world_rules:
        rules_text = "\n".join(f"  · {r}" for r in world_rules)
    else:
        rules_text = "（无特殊法则，遵循默认历史逻辑）"

    user_prompt = f"""【当前游戏状态】
{state_text}

【🗺️ 空间锚定 —— 皇帝的物理位置】
当前{era.dynasty_name}国都（皇帝所在城市）：{capital_id}（{capital_status}）
皇帝{era.default_ruler}本人就在 {capital_id} 城内！如果玩家的决策涉及迁都或逃亡，请在输出 JSON 中填写 capital_change 字段。

【🪐 当前生效的世界法则 —— 必须遵守】
{rules_text}

【危机事件】
标题：{title}
背景：{narrative}

【皇帝的应对决策】
{player_decision}

请根据上述游戏状态、生效的世界法则、危机背景和皇帝的决策，推演这一决策带来的历史后果。严格按照 JSON 格式输出裁决结果。"""

    return system_prompt, user_prompt


def build_audience_prompt(target: str, message: str) -> tuple[str, str]:
    """
    构造御前召见 Prompt（第一人称角色扮演模式）。

    参数:
        target: 召见目标
        message: 皇帝的最新对话内容

    返回:
        (system_prompt, user_prompt) 元组
    """
    import streamlit as st

    era = get_era_naming()
    system_prompt = _adapt_prompt_for_era(AUDIENCE_SYSTEM_PROMPT, era)

    state_text = _serialize_game_state(st.session_state)

    factions = st.session_state.get("factions", {})
    player_faction = st.session_state.get("player_faction", "")
    pf = factions.get(player_faction) if player_faction else None

    courtier_info = ""
    if pf and hasattr(pf, 'military') and pf.military:
        for u in pf.military:
            if u.general and target in u.general:
                courtier_info = (
                    f"姓名：{u.general}\n"
                    f"当前职务：统领{u.name}（{u.unit_type}，{u.size:,}人）\n"
                    f"驻防：{u.location}\n"
                    f"士气：{u.morale}"
                )
                break

    if not courtier_info:
        courtier_info = (
            f"姓名：{target}\n"
            f"身份：此人不在当前朝廷军制编制内。可能是宫中内侍、"
            f"{era.intel_org}暗探头目、新近由皇帝提拔的寒门亲信、宫廷秘密死士，"
            f"或是史书中未曾留名的隐没人物。请根据{era.era_name}的时代氛围、宫廷政治生态"
            f"和当前局势，为此人动态生成一个合理的人设来回应皇帝。"
        )

    audience = st.session_state.get("active_audience", {})
    chat_history = audience.get("chat_history", []) if audience else []

    history_text = ""
    if chat_history:
        history_text = "\n【对话历史】\n"
        for entry in chat_history[-10:]:
            role_label = "皇帝" if entry.get("role") == "user" else target
            history_text += f"{role_label}：{entry.get('content', '')}\n"

    user_prompt = f"""【当前局势】
{state_text}

【你的身份】
{target}
{courtier_info}
{history_text}
【皇帝刚才说】
{message}

请以 {target} 的身份，用第一人称直接回复皇帝。不要加任何前缀、标签或格式，直接说出你的回复。"""

    return system_prompt, user_prompt


# ---------------------------------------------------------------------------
# 动态势力命名 Prompt（轻量级，仅用于命名与分类）
# ---------------------------------------------------------------------------

FACTION_NAMING_SYSTEM_PROMPT = """你是一个为历史/魔幻战略游戏命名新势力的创意引擎。你的任务极其简单：根据势力标识符和触发描述，生成一个霸气的中文名并判断其类型。

规则：
1. 名称必须为中文，3-8个字，要有史诗感和压迫感——让人一听就知道这个势力不好惹。
2. 如果描述涉及丧尸/病毒/亡灵 → 类型选 ZombieHorde，名称偏末日恐怖风（如"天启尸潮""幽冥亡者军团"）。
3. 如果描述涉及外星/飞船/异星 → 类型选 Alien，名称偏科幻风（如"深空异星舰队""星河远征军"）。
4. 如果描述涉及修仙/魔法/灵气/宗门 → 类型选 Cult，名称偏仙侠风（如"太虚修仙联盟""九天玄女宗"）。
5. 如果描述涉及帝国/远征/舰队/殖民 → 类型选 Empire，名称偏历史风（如"大英皇家远征舰队"）。
6. 如果描述涉及部落/游牧/草原 → 类型选 Horde 或 Tribe。
7. 如果描述涉及起义/叛乱/造反 → 类型选 Rebel。
8. 默认情况下选 Empire。

仅输出 JSON，不要任何解释：
```json
{"name": "天启丧尸军团", "type": "ZombieHorde"}
```"""


def build_faction_naming_prompt(faction_id: str, description: str = "") -> str:
    """
    构造动态势力命名 Prompt。

    参数:
        faction_id: 势力标识符（如 "zombie_virus_horde"）
        description: 触发描述（如 "玩家触发了僵尸病毒爆发"）

    返回:
        user_prompt 字符串
    """
    desc_text = description if description else f"势力ID为 {faction_id}，请根据ID推测其特征。"
    return f"""请为以下新出现的势力生成一个霸气的中文名并判断其类型。

势力标识符：{faction_id}
触发描述：{desc_text}

请直接输出 JSON，不要添加任何解释。"""


# ---------------------------------------------------------------------------
# 状态序列化
# ---------------------------------------------------------------------------

def _serialize_game_state(session) -> str:
    """将 st.session_state 中的游戏状态序列化为精简文本。"""
    lines: list[str] = []

    # 时间
    year = session.get("year", 0)
    month = session.get("month", 1)
    season = session.get("season", "春")
    year_label = f"公元前{abs(year)}年" if year < 0 else f"公元{year}年"
    lines.append(f"时间：{year_label} {month}月（{season}） 第{session.get('turn_number', 0)}回合")

    # 玩家势力
    player_faction = session.get("player_faction", "")
    factions = session.get("factions", {})
    pf = factions.get(player_faction) if player_faction else None
    resources = session.get("resources", {}).get(player_faction, {})

    if pf:
        lines.append(f"\n【玩家势力】{pf.name}（{pf.ruler}）")
        lines.append(f"  政体：{pf.government}  首都：{pf.capital}")
        lines.append(f"  状态：{pf.status}")
        lines.append(f"  国库：{resources.get('treasury', 0):,} 两白银")
        lines.append(f"  兵力：{resources.get('manpower', 0):,} 人")
        lines.append(f"  粮草：{resources.get('food', 0):,} 石")
        lines.append(f"  民心：{resources.get('stability', 0)}%")
        lines.append(f"  威望：{resources.get('prestige', 0)}%")
        lines.append(f"  腐败度：{resources.get('corruption', 0)}%")

        # 军队
        military = pf.military if hasattr(pf, 'military') else []
        if military:
            lines.append("  军队部署：")
            for u in military:
                lines.append(f"    - {u.name}（{u.unit_type}）{u.size:,}人 "
                             f"驻{u.location} 士气{u.morale} 将领：{u.general or '无'}")

    # 领土
    territory = session.get("territory", {})
    pf_regions = [r for r, f in territory.items() if f == player_faction]
    lines.append(f"\n【控制区域】（共 {len(pf_regions)} 处）")
    lines.append(f"  {', '.join(pf_regions[:20])}" + ("..." if len(pf_regions) > 20 else ""))

    # 其他势力
    lines.append("\n【其他势力】")
    diplomacy = session.get("diplomacy", [])
    for fid, faction in factions.items():
        if fid == player_faction:
            continue
        resources_other = session.get("resources", {}).get(fid, {})
        rel_status = "中立"
        for rel in diplomacy:
            a = rel.faction_a if hasattr(rel, 'faction_a') else rel.get('faction_a', '')
            b = rel.faction_b if hasattr(rel, 'faction_b') else rel.get('faction_b', '')
            if (a == player_faction and b == fid) or (b == player_faction and a == fid):
                status = rel.status if hasattr(rel, 'status') else rel.get('status', '')
                rel_status = status
                break

        regions_count = sum(1 for r, f in territory.items() if f == fid)
        lines.append(
            f"  {faction.name}（{faction.ruler}）- "
            f"关系：{rel_status} | "
            f"兵力：{resources_other.get('manpower', 0):,} | "
            f"领土：{regions_count} 区 | "
            f"状态：{faction.status}"
        )

    # 世界法则
    world_rules = session.get("world_rules", [])
    if world_rules:
        lines.append(f"\n【生效中的世界法则】（共 {len(world_rules)} 条）")
        for i, rule in enumerate(world_rules, 1):
            lines.append(f"  {i}. {rule}")

    # 可用区域 ID 列表（供 LLM 在 territory_changes 中参考）
    lines.append(f"\n【可用 region_id 列表】")
    all_regions = sorted(set(territory.keys()))
    lines.append(f"  {', '.join(all_regions[:30])}")
    if len(all_regions) > 30:
        lines.append(f"  ...（共 {len(all_regions)} 个区域）")

    return "\n".join(lines)
