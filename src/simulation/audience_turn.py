"""
御前召见私密对话引擎 —— 第一人称角色扮演管线

核心原则：
  - 对话结果仅追加到 st.session_state.active_audience['chat_history']
  - 绝不写入编年史 (chronicle_log)
  - 绝不修改游戏数值 (effects/territory/diplomacy)
  - 不消耗任何行动力（绝对皇权沙盒）
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.llm.client import generate_response
from src.llm.prompt_builder import build_audience_prompt


def execute_audience_chat(target: str, message: str) -> dict[str, Any]:
    """
    执行一次御前私密对话。

    如果 active_audience 为空，则自动开启新的召见会话。
    结果追加到 active_audience['chat_history']，不写入编年史。

    参数:
        target: 召见对象姓名
        message: 皇帝的最新发言
    """
    # ---- 初始化或恢复会话 ----
    audience = st.session_state.get("active_audience")

    if not audience or audience.get("target") != target:
        # 新会话
        audience = {
            "target": target,
            "chat_history": [],
        }
        st.session_state.active_audience = audience

    # ---- 记录皇帝发言 ----
    audience["chat_history"].append({"role": "user", "content": message})

    # ---- 构造 Prompt ----
    system_prompt, user_prompt = build_audience_prompt(target, message)

    # ---- 调用 LLM ----
    try:
        raw_response = generate_response(user_prompt, system_prompt)
    except Exception as e:
        audience["chat_history"].append({
            "role": "assistant",
            "content": f"（{target}沉默不语，似有难言之隐……）",
        })
        return {"ok": True, "reply": audience["chat_history"][-1]["content"], "target": target}

    # ---- 清洗回复（移除可能的 JSON 残留、代码块标记等） ----
    reply = _clean_response(raw_response)

    # ---- 记录臣子回复 ----
    audience["chat_history"].append({"role": "assistant", "content": reply})

    return {"ok": True, "reply": reply, "target": target}


def end_audience() -> None:
    """结束当前召见，清空 active_audience。"""
    st.session_state.active_audience = None


# ---------------------------------------------------------------------------
# 内部
# ---------------------------------------------------------------------------

def _clean_response(raw: str) -> str:
    """清洗 LLM 原始输出，移除 JSON/代码块等格式残留。"""
    text = raw.strip()

    # 移除 ```json ... ``` 代码块
    if text.startswith("```"):
        # 找到第一个换行后的内容
        idx = text.find("\n")
        if idx != -1:
            text = text[idx + 1:]
        # 移除结尾的 ```
        if text.endswith("```"):
            text = text[:-3]

    # 如果看起来像 JSON，尝试提取 narrative 字段
    if text.startswith("{") and text.endswith("}"):
        try:
            import json
            parsed = json.loads(text)
            if "narrative" in parsed:
                return parsed["narrative"].strip()
            if "reply" in parsed:
                return parsed["reply"].strip()
            if "content" in parsed:
                return parsed["content"].strip()
        except (json.JSONDecodeError, TypeError):
            pass

    # 移除常见的 LLM 前缀
    prefixes = [
        f"（{st.session_state.get('active_audience', {}).get('target', '臣子')}）",
        "臣子说：", "回复：", "回答：", "答：",
    ]
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()

    return text.strip()
