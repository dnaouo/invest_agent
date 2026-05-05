"""Event Agent — 事件驱动分析节点。"""
from __future__ import annotations

import json
from pathlib import Path

from agents.state import MarketState
from sandboxes.data import tushare_client
from llm_clients.kimi_sync import call_kimi
from llm_clients.tier_router import get_tier_config


_PROMPT_PATH = Path(__file__).parent / "prompts" / "event.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _fetch_data(ts_code: str, trade_date: str) -> dict:
    """拉取事件驱动分析需要的全部数据。"""
    data = {}

    start = str(int(trade_date) - 100)

    anns = tushare_client.get_anns_d(ts_code=ts_code, start_date=start, end_date=trade_date)
    if anns["status"] == "ok":
        data["anns_d"] = anns["data"][:20]

    share_float = tushare_client.get_share_float(ts_code=ts_code)
    if share_float["status"] == "ok":
        data["share_float"] = share_float["data"][:10]

    holdertrade = tushare_client.get_stk_holdertrade(ts_code=ts_code, start_date=start, end_date=trade_date)
    if holdertrade["status"] == "ok":
        data["stk_holdertrade"] = holdertrade["data"][:10]

    forecast = tushare_client.get_forecast(ts_code=ts_code)
    if forecast["status"] == "ok":
        data["forecast"] = forecast["data"][:5]

    return data


def event_node(state: MarketState) -> dict:
    """LangGraph 节点函数：事件驱动分析。"""
    ts_code = state["ts_code"]
    trade_date = state["trade_date"]
    stock_name = state.get("stock_name", ts_code)

    data = _fetch_data(ts_code, trade_date)

    system_prompt = _load_prompt()
    user_message = (
        f"请分析 {stock_name}（{ts_code}）截至 {trade_date} 的事件驱动因素。\n\n"
        f"以下是数据：\n{json.dumps(data, ensure_ascii=False, default=str)}"
    )

    tier = get_tier_config("event")
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
            "events": [{"type": "other", "strength": 0.0, "detail": "LLM 输出解析失败"}],
            "data_sources": list(data.keys()),
            "summary": content[:500],
        }

    return {"event_analysis": result}
