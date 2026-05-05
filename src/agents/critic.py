"""Critic Agent — 独立挑刺节点（GAN 模式）。"""
from __future__ import annotations

import json
from pathlib import Path

from agents.state import MarketState
from llm_clients.kimi_sync import call_kimi
from llm_clients.tier_router import get_tier_config

_PROMPT_PATH = Path(__file__).parent / "prompts" / "critic.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _format_prior_analysis(state: MarketState) -> str:
    """将前序 agent 的分析结果格式化为文本。"""
    parts = []

    if "fundamental_score" in state:
        parts.append(f"## 基本面分析\n{json.dumps(state['fundamental_score'], ensure_ascii=False, default=str)}")
    if "technical_score" in state:
        parts.append(f"## 技术面分析\n{json.dumps(state['technical_score'], ensure_ascii=False, default=str)}")
    if "macro_themes" in state:
        parts.append(f"## 宏观/主题分析\n{json.dumps(state['macro_themes'], ensure_ascii=False, default=str)}")
    if "event_analysis" in state:
        parts.append(f"## 事件分析\n{json.dumps(state['event_analysis'], ensure_ascii=False, default=str)}")
    if "flow_institutional" in state:
        parts.append(f"## 机构资金\n{json.dumps(state['flow_institutional'], ensure_ascii=False, default=str)}")
    if "flow_hot_money" in state:
        parts.append(f"## 游资动向\n{json.dumps(state['flow_hot_money'], ensure_ascii=False, default=str)}")
    if "risk_assessment" in state:
        parts.append(f"## 风控评估\n{json.dumps(state['risk_assessment'], ensure_ascii=False, default=str)}")
    if "backtest_result" in state:
        parts.append(f"## 回测结果\n{json.dumps(state['backtest_result'], ensure_ascii=False, default=str)}")

    if not parts:
        return "（暂无前序分析结果）"

    return "\n\n".join(parts)


def critic_node(state: MarketState) -> dict:
    """LangGraph 节点函数：独立挑刺评审。"""
    ts_code = state.get("ts_code", "")
    stock_name = state.get("stock_name", ts_code)

    system_prompt = _load_prompt()
    prior_analysis = _format_prior_analysis(state)

    user_message = f"请对 {stock_name}（{ts_code}）的以下分析进行独立评审：\n\n{prior_analysis}"

    tier = get_tier_config("critic")
    response = call_kimi(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        **tier,
    )

    content = response["content"]
    try:
        start_idx = content.index("{")
        end_idx = content.rindex("}") + 1
        result = json.loads(content[start_idx:end_idx])
        if "score" in result:
            result["verdict"] = "pass" if result["score"] >= 60 else "reject"
    except (ValueError, json.JSONDecodeError):
        result = {
            "score": 50,
            "objections": ["Critic LLM 输出解析失败"],
            "worst_case": "无法评估",
            "verdict": "reject",
        }

    return {"critic_review": result}
