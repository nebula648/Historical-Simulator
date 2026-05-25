"""
JSON 提取器 —— 从 LLM 响应中安全提取 JSON 块
"""

from __future__ import annotations

import json
import re
from typing import Any


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def extract_json(text: str) -> dict[str, Any]:
    """
    从 LLM 响应文本中提取 JSON 数据。

    策略（按优先级）：
      1. 匹配 ```json ... ``` 代码块
      2. 匹配 ``` ... ``` 任意代码块
      3. 匹配裸 JSON 对象 { ... }
      4. 全部失败则返回空 dict（此时应调用 text_sniffer）

    返回:
        解析成功的 dict，或空 dict
    """
    if not text or not text.strip():
        return {}

    # 策略 1: ```json ... ```
    match = re.search(r"```json\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return _safe_parse(match.group(1).strip())

    # 策略 2: ``` ... ```
    match = re.search(r"```\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        result = _safe_parse(match.group(1).strip())
        if result:
            return result

    # 策略 3: 裸 JSON 对象
    # 找到第一个 { 和对应的 }
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        result = _safe_parse(match.group(0))
        if result:
            return result

    # 全部失败
    return {}


def _safe_parse(json_str: str) -> dict[str, Any]:
    """尝试解析 JSON 字符串，失败返回空 dict。"""
    try:
        data = json.loads(json_str)
        if isinstance(data, dict):
            return data
        # 如果是 list，包装为 dict
        return {"items": data}
    except (json.JSONDecodeError, ValueError):
        # 尝试修复常见错误：尾部逗号、单引号
        cleaned = _attempt_repair(json_str)
        if cleaned:
            try:
                data = json.loads(cleaned)
                return data if isinstance(data, dict) else {"items": data}
            except (json.JSONDecodeError, ValueError):
                pass
    return {}


def _attempt_repair(json_str: str) -> str | None:
    """尝试修复常见的 JSON 格式错误。"""
    s = json_str.strip()
    # 移除尾部逗号
    s = re.sub(r",\s*}", "}", s)
    s = re.sub(r",\s*\]", "]", s)
    # 如果看起来还是不像 JSON，放弃
    if not (s.startswith("{") and s.endswith("}")):
        return None
    return s
