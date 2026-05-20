"""Tier-based model parameter router for Kimi K2.6 agents."""

from __future__ import annotations

import os

TIER_CONFIG: dict[str, dict] = {
    "A": {"thinking": True, "max_tokens": 32768},
    "B_thinking": {"thinking": True, "max_tokens": 8192},
    "B_recall": {"thinking": False, "max_tokens": 8192},
}

AGENT_TIER_MAP: dict[str, str] = {
    "supervisor": "A",
    "critic": "A",
    "risk": "B_recall",
    "macro": "B_recall",
    "event": "B_recall",
    "flow_hot": "B_recall",
    "fund": "B_recall",
    "tech": "B_recall",
    "flow_inst": "B_recall",
    "backtest": "B_recall",
    "hypothesis_scan": "B_recall",
    "hypothesis_verify": "B_recall",
    "hypothesis_judge": "B_thinking",
    "hypothesis_critic": "A",
}

_DEFAULT_TIER = "B_recall"

# lite 档：仅这几个关键阶段保留 thinking，其余全部强制关
_LITE_CRITICAL_AGENTS = {
    "hypothesis_verify",
    "hypothesis_judge",
    "hypothesis_critic",
    "memo_writer",
    "supervisor",
    "critic",
}


def get_tier_config(agent_name: str) -> dict:
    """返回该 agent 对应的 Kimi 调用参数 {"thinking": bool, "max_tokens": int}

    受 env KIMI_THINKING_LEVEL 覆盖：
    - "full"（默认 / 未设置时等价）：所有 agent 按 AGENT_TIER_MAP 原样配置
    - "lite"：仅 hypothesis_verify/judge/critic + memo_writer/supervisor/critic 强制开 thinking，其余强制关
    - "off"：所有 agent 强制 thinking=False（应急快速跑）
    """
    tier = AGENT_TIER_MAP.get(agent_name, _DEFAULT_TIER)
    cfg = dict(TIER_CONFIG[tier])
    level = os.environ.get("KIMI_THINKING_LEVEL", "full").lower()
    if level == "off":
        cfg["thinking"] = False
    elif level == "lite":
        cfg["thinking"] = agent_name in _LITE_CRITICAL_AGENTS
    # full 不覆盖
    return cfg
