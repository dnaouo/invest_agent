"""Risk Agent — 风控评估节点。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from agents.state import MarketState
from sandboxes.data import tushare_client
from llm_clients.kimi_sync import call_kimi
from llm_clients.tier_router import get_tier_config


_PROMPT_PATH = Path(__file__).parent / "prompts" / "risk.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _fetch_data(ts_code: str, trade_date: str) -> dict:
    """拉取风控评估需要的全部数据。"""
    data = {}

    pledge = tushare_client.get_pledge_stat(ts_code=ts_code)
    if pledge["status"] == "ok":
        data["pledge_stat"] = pledge["data"][:5]

    def _subtract_days(date_str: str, days: int) -> str:
        dt = datetime.strptime(date_str, "%Y%m%d")
        return (dt - timedelta(days=days)).strftime("%Y%m%d")

    start = _subtract_days(trade_date, 100)
    holdertrade = tushare_client.get_stk_holdertrade(
        ts_code=ts_code, start_date=start, end_date=trade_date,
    )
    if holdertrade["status"] == "ok":
        data["stk_holdertrade"] = holdertrade["data"][:10]

    share_float = tushare_client.get_share_float(ts_code=ts_code)
    if share_float["status"] == "ok":
        data["share_float"] = share_float["data"][:5]

    return data


def risk_node(state: MarketState) -> dict:
    """LangGraph 节点函数：风控评估。"""
    ts_code = state["ts_code"]
    trade_date = state["trade_date"]
    stock_name = state.get("stock_name", ts_code)

    data = _fetch_data(ts_code, trade_date)

    system_prompt = _load_prompt()
    user_message = (
        f"请对 {stock_name}（{ts_code}）截至 {trade_date} 进行风控评估。\n\n"
        f"以下是数据：\n{json.dumps(data, ensure_ascii=False, default=str)}"
    )

    tier = get_tier_config("risk")
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
            "score": 50,
            "risk_flags": ["LLM 输出解析失败"],
            "position_suggestion": {"max_pct": 5.0, "stop_loss": 0.0},
            "data_sources": list(data.keys()),
            "summary": content[:500],
        }

    return {"risk_assessment": result}
