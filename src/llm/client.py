"""
LLM 客户端封装
统一接口：generate_response(prompt, system_prompt) -> str
支持 DeepSeek / Anthropic Claude / OpenAI / 自定义中转站 API。

【硬熔断设计】
  唯一密钥来源：st.session_state.user_api_key（由用户在侧边栏手动输入）。
  绝不读取 os.environ、.env、st.secrets 或任何硬编码默认 Key。
  若未检测到有效密钥，在 generate_response() 入口处立即触发熔断，
  抛出 RuntimeError 阻断后续一切 API 调用，防止消耗开发者额度。
"""

from __future__ import annotations

import streamlit as st

# 密钥最短长度阈值
_MIN_KEY_LENGTH = 10

# 占位符模式（触发熔断）
_PLACEHOLDER_PATTERNS = [
    "your-deepseek", "your-key-here", "your-api", "sk-ant-your",
    "sk-your", "your-anthropic", "your-openai", "placeholder",
    "xxxxxxxx", "sk-...", "sk-xxxx",
]


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def is_api_key_configured() -> bool:
    """检查 session_state 中是否存在有效的用户 API Key。"""
    key = _get_user_key()
    return _is_key_valid(key)


def generate_response(prompt: str, system_prompt: str = "") -> str:
    """
    统一 LLM 调用接口。

    【硬熔断】入口处校验 user_api_key 有效性，不通过则直接抛出 RuntimeError。
    通过后按 vendor 选择底层 API 发起请求。

    返回 LLM 的原始文本响应。
    """
    user_key = _get_user_key()
    _validate_key_or_die(user_key)

    vendor = st.session_state.get("api_vendor", "DeepSeek")
    vendor_map = {
        "DeepSeek": _call_deepseek,
        "Anthropic (Claude)": _call_anthropic,
        "OpenAI": _call_openai,
        "自定义中转站": _call_custom,
    }
    caller = vendor_map.get(vendor, _call_deepseek)

    try:
        return caller(prompt, system_prompt, user_key)
    except Exception as e:
        raise RuntimeError(
            f"【{vendor}】API 调用失败。"
            f"请检查 API Key 是否正确、网络是否畅通、账户余额是否充足。\n"
            f"详细错误：{e}"
        )


# ---------------------------------------------------------------------------
# 硬熔断：密钥校验
# ---------------------------------------------------------------------------

def _validate_key_or_die(key: str) -> None:
    """
    硬熔断判定 —— 不满足任一条件立即抛出 RuntimeError：
      1. key 非空
      2. key 长度 >= 10
      3. key 不是已知占位符
    """
    if not key or not key.strip():
        raise RuntimeError(
            "❌ 【核心熔断】天机阁未能感应到密钥能量！\n"
            "当前未配置有效的 API Key，系统已拦截本次推演请求，以防消耗开发者额度。\n"
            "请在侧边栏「🔑 LLM 驱动引擎配置」中输入您的 API Key。"
        )

    key_stripped = key.strip()

    if len(key_stripped) < _MIN_KEY_LENGTH:
        raise RuntimeError(
            f"❌ 【核心熔断】密钥长度不足（{len(key_stripped)} 字符，最少需要 {_MIN_KEY_LENGTH} 字符）。\n"
            "请确认您在侧边栏输入的是完整的 API Key。"
        )

    if _is_placeholder(key_stripped):
        raise RuntimeError(
            "❌ 【核心熔断】检测到占位符密钥（如 sk-... 或 your-key-here）。\n"
            "请在侧边栏「🔑 LLM 驱动引擎配置」中输入您的真实 API Key。"
        )


# ---------------------------------------------------------------------------
# 内部：密钥读取（唯一来源：session_state）
# ---------------------------------------------------------------------------

def _get_user_key() -> str:
    """从 session_state 读取用户注入的 API Key —— 这是唯一合法的密钥来源。"""
    try:
        return st.session_state.get("user_api_key", "")
    except Exception:
        return ""


def _is_key_valid(key: str) -> bool:
    """判断 key 是否有效（非空、足够长、非占位符）。"""
    if not key or not key.strip():
        return False
    if len(key.strip()) < _MIN_KEY_LENGTH:
        return False
    if _is_placeholder(key.strip()):
        return False
    return True


def _is_placeholder(value: str) -> bool:
    """判断字符串是否为占位符。"""
    val_lower = value.lower()
    return any(p in val_lower for p in _PLACEHOLDER_PATTERNS)


# ---------------------------------------------------------------------------
# DeepSeek API
# ---------------------------------------------------------------------------

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"


def _call_deepseek(prompt: str, system_prompt: str, api_key: str) -> str:
    """调用 DeepSeek Chat API。"""
    import requests

    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": messages,
                "temperature": 0.8,
                "max_tokens": 4096,
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    except requests.exceptions.Timeout:
        raise RuntimeError("DeepSeek API 请求超时（120s），请检查网络连接或稍后重试。")
    except requests.exceptions.HTTPError as e:
        detail = ""
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise RuntimeError(f"DeepSeek API 返回 HTTP 错误 ({resp.status_code})：{detail}")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"无法连接 DeepSeek API ({DEEPSEEK_BASE_URL})。"
            "请检查网络连接，或确认是否需要配置代理。"
        )
    except KeyError:
        raise RuntimeError("DeepSeek API 返回格式异常，无法解析响应。")


# ---------------------------------------------------------------------------
# Anthropic Claude API
# ---------------------------------------------------------------------------

ANTHROPIC_MODEL = "claude-sonnet-4-6"


def _call_anthropic(prompt: str, system_prompt: str, api_key: str) -> str:
    """调用 Anthropic Claude API。"""
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("未安装 anthropic SDK。请运行：pip install anthropic")

    try:
        client = anthropic.Anthropic(api_key=api_key)
        kwargs: dict = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 4096,
            "temperature": 0.8,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = client.messages.create(**kwargs)
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            raise RuntimeError("Anthropic API Key 无效或已过期，请检查。")
        elif "429" in error_msg or "rate" in error_msg.lower():
            raise RuntimeError("Anthropic API 请求频率超限，请稍后重试。")
        elif "529" in error_msg or "overloaded" in error_msg.lower():
            raise RuntimeError("Anthropic 服务端过载，请稍后重试。")
        else:
            raise RuntimeError(f"Anthropic API 调用失败：{error_msg}")


# ---------------------------------------------------------------------------
# OpenAI API
# ---------------------------------------------------------------------------

OPENAI_MODEL = "gpt-4o"


def _call_openai(prompt: str, system_prompt: str, api_key: str) -> str:
    """调用 OpenAI Chat API。"""
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("未安装 openai SDK。请运行：pip install openai")

    try:
        client = OpenAI(api_key=api_key)
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.8,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Incorrect API key" in error_msg:
            raise RuntimeError("OpenAI API Key 无效或已过期，请检查。")
        elif "429" in error_msg or "rate" in error_msg.lower():
            raise RuntimeError("OpenAI API 请求频率超限，请稍后重试。")
        else:
            raise RuntimeError(f"OpenAI API 调用失败：{error_msg}")


# ---------------------------------------------------------------------------
# 自定义中转站 API（OpenAI 兼容协议）
# ---------------------------------------------------------------------------

CUSTOM_DEFAULT_MODEL = "gpt-4o"


def _call_custom(prompt: str, system_prompt: str, api_key: str) -> str:
    """调用自定义中转站 API（兼容 OpenAI 协议）。"""
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("未安装 openai SDK。请运行：pip install openai")

    base_url = st.session_state.get("custom_api_base", "https://api.openai.com/v1").strip()
    model = st.session_state.get("custom_api_model", CUSTOM_DEFAULT_MODEL).strip()

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.8,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""

    except Exception as e:
        error_msg = str(e)
        raise RuntimeError(f"自定义中转站 API 调用失败 (base_url={base_url})：{error_msg}")
