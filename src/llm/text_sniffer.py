"""
【防幻觉核心】纯文本嗅探器 (Text-Fallback Sniffer)

当 LLM 忘记输出标准 JSON 时，从纯文本中通过正则/NLP 提取
数值变更和叙事内容，构造兜底 dict。
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# 资源关键词 → session key 映射
# ---------------------------------------------------------------------------

RESOURCE_PATTERNS: dict[str, list[str]] = {
    "treasury":   ["国库", "银两", "白银", "财赋", "帑银", "府库", "钱粮", "饷银"],
    "manpower":   ["兵力", "兵马", "士卒", "兵员", "军队", "将士", "军士", "募兵"],
    "food":       ["粮草", "粮食", "粮秣", "军粮", "米粟", "储粮", "屯粮"],
    "stability":  ["民心", "人心", "民意", "民情", "社会安定", "百姓安居"],
    "prestige":   ["威望", "声威", "威信", "天子威仪", "朝廷威严", "国威"],
    "corruption": ["腐败", "贪腐", "吏治", "贪墨", "蠹虫", "舞弊", "中饱"],
}

# 正负向变化模式
INCREASE_PATTERNS = [
    r"(KEYWORD)\s*[增加上升提高增长扩充增]+[了至到]?\s*(\d+)",
    r"[增加上升提高增长扩充增]{{1,3}}\s*(KEYWORD)\s*(\d+)",
    r"\+(\d+)\s*(KEYWORD)",
    r"(KEYWORD)\s*\+(\d+)",
]

DECREASE_PATTERNS = [
    r"(KEYWORD)\s*[减少下降降低损失消耗折损减]+[了至到]?\s*(\d+)",
    r"[减少下降降低损失消耗折损减]{{1,3}}\s*(KEYWORD)\s*(\d+)",
    r"\-(\d+)\s*(KEYWORD)",
    r"(KEYWORD)\s*\-(\d+)",
]


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def sniff(text: str) -> dict[str, Any]:
    """
    从纯文本中嗅探游戏数据变更。

    返回格式与 LLM JSON 输出一致:
        {
            "narrative": str,
            "effects": {resource_key: int, ...},
            "territory_changes": [],
            "diplomacy_changes": [],
            "_fallback": True   # 标记此结果来自嗅探器
        }
    """
    effects = _extract_resource_changes(text)
    narrative = _extract_narrative(text)
    territory = _extract_territory_changes(text)

    return {
        "narrative": narrative,
        "effects": effects,
        "territory_changes": territory,
        "diplomacy_changes": [],
        "_fallback": True,
    }


def sniff_and_merge(text: str, partial_json: dict) -> dict[str, Any]:
    """
    以 partial_json（来自 json_extractor 的部分解析结果）为基础，
    用嗅探器结果补充缺失的字段。
    """
    sniffed = sniff(text)
    merged: dict[str, Any] = {
        "narrative": partial_json.get("narrative") or sniffed["narrative"],
        "effects": partial_json.get("effects") or sniffed["effects"],
        "territory_changes": partial_json.get("territory_changes") or sniffed["territory_changes"],
        "diplomacy_changes": partial_json.get("diplomacy_changes") or sniffed["diplomacy_changes"],
        "_fallback": sniffed.get("_fallback", False),
    }
    return merged


# ---------------------------------------------------------------------------
# 内部：数值变更提取
# ---------------------------------------------------------------------------

def _extract_resource_changes(text: str) -> dict[str, int]:
    """从文本中提取各资源的数值变更。"""
    effects: dict[str, int] = {}

    for resource_key, keywords in RESOURCE_PATTERNS.items():
        net_change = 0

        for kw in keywords:
            escaped = re.escape(kw)
            # 正增长
            for pattern in INCREASE_PATTERNS:
                full_pattern = pattern.replace("KEYWORD", escaped)
                for match in re.finditer(full_pattern, text):
                    # group(2) 是数字，group(1) 是关键词
                    groups = match.groups()
                    val = int(groups[-1])  # 最后一个捕获组是数字
                    net_change += val

            # 负增长
            for pattern in DECREASE_PATTERNS:
                full_pattern = pattern.replace("KEYWORD", escaped)
                for match in re.finditer(full_pattern, text):
                    groups = match.groups()
                    val = int(groups[-1])
                    net_change -= val

        if net_change != 0:
            effects[resource_key] = net_change

    return effects


def _extract_narrative(text: str) -> str:
    """提取主要叙事文本。去掉 JSON 块后取最长段落。"""
    # 移除代码块
    cleaned = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # 移除 JSON 对象
    cleaned = re.sub(r"\{.*\}", "", cleaned, flags=re.DOTALL)
    # 按双换行分割
    paragraphs = [p.strip() for p in cleaned.split("\n\n") if len(p.strip()) > 20]
    if paragraphs:
        # 返回最长段落作为叙事
        return max(paragraphs, key=len)
    # 返回整体文本的前 500 字
    return cleaned.strip()[:500]


def _extract_territory_changes(text: str) -> list[dict]:
    """从文本中提取领土变更。"""
    changes: list[dict] = []
    # 模式: 某某 占领/攻占/夺取/收复/丢失 某某地
    pattern = r"(大[明清顺西]|清军|明军|顺军|西军|我军|敌军)?[^，。,\.]{0,10}(占领|攻占|夺取|收复|陷落|丢失|陷于|攻陷|克复|得而复失)[^，。,\.]{0,10}([A-Za-z_]+|[京津沪渝冀晋辽吉黑苏浙皖闽赣鲁豫鄂湘粤桂琼川贵云藏陕甘青宁新台])"
    for match in re.finditer(pattern, text):
        changes.append({
            "text": match.group(0).strip(),
            "_sniffed": True,
        })
    return changes
