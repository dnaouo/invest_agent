"""Supervisor Agent — 综合评分 + 最终信号输出。"""
from __future__ import annotations

import json
from pathlib import Path

from agents.state import MarketState
from llm_clients.kimi_sync import call_kimi
from llm_clients.tier_router import get_tier_config

_PROMPT_PATH = Path(__file__).parent / "prompts" / "supervisor.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _format_all_analyses(state: MarketState) -> str:
    sections = {
        "fundamental_score": "基本面分析",
        "technical_score": "技术面分析",
        "macro_themes": "宏观/主题分析",
        "event_analysis": "事件分析",
        "flow_institutional": "机构资金",
        "flow_hot_money": "游资动向",
        "risk_assessment": "风控评估",
        "backtest_result": "回测结果",
        "critic_review": "Critic 评审",
    }
    parts = []
    for key, title in sections.items():
        if key in state and state[key]:
            parts.append(f"## {title}\n{json.dumps(state[key], ensure_ascii=False, default=str)}")
    return "\n\n".join(parts) if parts else "（无分析结果）"


def _compute_weighted_score(state: MarketState) -> dict:
    scores = {
        "fund": state.get("fundamental_score", {}).get("score", 50),
        "macro": state.get("macro_themes", {}).get("score", 50),
        "tech": state.get("technical_score", {}).get("score", 50),
        "event": state.get("event_analysis", {}).get("score", 50),
        "flow_inst": state.get("flow_institutional", {}).get("score", 50),
        "flow_hot": state.get("flow_hot_money", {}).get("score", 50),
        "risk": state.get("risk_assessment", {}).get("score", 50),
        "backtest": state.get("backtest_result", {}).get("score", 50),
    }
    is_event_driven = scores["event"] > scores["fund"]
    if is_event_driven:
        weights = {"event": 0.25, "flow_hot": 0.20, "macro": 0.15, "fund": 0.15, "risk": 0.15, "tech": 0.05, "flow_inst": 0.03, "backtest": 0.02}
    else:
        weights = {"fund": 0.30, "macro": 0.20, "tech": 0.15, "risk": 0.20, "event": 0.05, "flow_inst": 0.05, "flow_hot": 0.03, "backtest": 0.02}
    weighted = sum(scores[k] * weights[k] for k in weights)
    return {
        "weighted_score": round(weighted, 1),
        "type": "event_driven" if is_event_driven else "fundamental_driven",
        "weights": weights,
    }


def supervisor_node(state: MarketState) -> dict:
    ts_code = state.get("ts_code", "")
    stock_name = state.get("stock_name", ts_code)

    weighted_info = _compute_weighted_score(state)
    system_prompt = _load_prompt()
    analyses = _format_all_analyses(state)
    user_message = (
        f"请为 {stock_name}（{ts_code}）综合以下分析，输出最终投资信号：\n\n"
        f"加权信息：{json.dumps(weighted_info, ensure_ascii=False)}\n\n{analyses}"
    )

    tier = get_tier_config("supervisor")
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
    except (ValueError, json.JSONDecodeError):
        result = {
            "direction": "hold",
            "confidence": 0.0,
            "position_pct": 0.0,
            "reasons": ["Supervisor LLM 输出解析失败"],
            "summary": content[:500],
        }

    if state.get("critic_review", {}).get("verdict") == "reject":
        result["direction"] = "hold"
        result["confidence"] = 0.0
        result["position_pct"] = 0.0
        result.setdefault("reasons", []).append("Critic 否决，强制 hold")

    result["_weighted_info"] = weighted_info
    return {"supervisor_signal": result}
