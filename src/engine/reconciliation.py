"""
【防幻觉核心】前端强制对账器

职责：
  1. 记录 LLM 声称的数值变更（claimed_deltas）
  2. 执行 engine/resource.py 的实际变更
  3. 对比 claimed vs actual
  4. 若不一致 → 标红报警，以 engine 实际值为准
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import streamlit as st


@dataclass
class ReconciliationReport:
    """单次对账报告。"""
    turn: int
    claimed_effects: dict[str, int]     # LLM 声称的变更
    actual_deltas: dict[str, int]       # engine 实际执行的变更
    discrepancies: list[str]            # 差异描述
    is_clean: bool                      # 是否完全一致
    used_fallback: bool = False         # 是否启用了 text_sniffer


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def reconcile(
    claimed_effects: dict[str, int],
    actual_deltas: list,
    used_fallback: bool = False,
) -> ReconciliationReport:
    """
    执行对账：对比 LLM 声称的变更 vs 引擎实际变更。

    参数:
        claimed_effects: LLM 返回的 effects dict
        actual_deltas: ResourceDelta 列表（来自 resource.apply_effects）
        used_fallback: 是否使用了 text_sniffer

    返回:
        ReconciliationReport
    """
    # 汇总实际变更
    actual_dict: dict[str, int] = {}
    for d in actual_deltas:
        key = d.resource_key if hasattr(d, 'resource_key') else d.get('resource_key', '')
        delta = d.delta if hasattr(d, 'delta') else d.get('delta', 0)
        if key:
            actual_dict[key] = actual_dict.get(key, 0) + delta

    # 对比
    discrepancies: list[str] = []
    all_keys = set(claimed_effects.keys()) | set(actual_dict.keys())

    for key in sorted(all_keys):
        claimed = claimed_effects.get(key, 0)
        actual = actual_dict.get(key, 0)
        if claimed != actual:
            discrepancies.append(
                f"{key}: LLM声称 {claimed:+d}, 引擎实际 {actual:+d} (差异 {actual - claimed:+d})"
            )

    report = ReconciliationReport(
        turn=st.session_state.get("turn_number", 0),
        claimed_effects=dict(claimed_effects),
        actual_deltas=dict(actual_dict),
        discrepancies=discrepancies,
        is_clean=len(discrepancies) == 0,
        used_fallback=used_fallback,
    )

    # 存储到 session 供 UI 展示
    reports = st.session_state.get("reconciliation_reports", [])
    reports.append(report)
    # 只保留最近 20 条
    st.session_state.reconciliation_reports = reports[-20:]

    return report


def get_last_report() -> ReconciliationReport | None:
    """获取最近一次对账报告。"""
    reports = st.session_state.get("reconciliation_reports", [])
    return reports[-1] if reports else None
