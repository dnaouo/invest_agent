"""Technical/Factor Agent — 技术面分析节点。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from agents.state import MarketState
from sandboxes.data import tushare_client
from llm_clients.kimi_sync import call_kimi
from llm_clients.tier_router import get_tier_config


_PROMPT_PATH = Path(__file__).parent / "prompts" / "technical.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _fetch_data(ts_code: str, trade_date: str) -> dict:
    """拉取技术面分析需要的全部数据。"""
    data = {}

    def _subtract_days(date_str: str, days: int) -> str:
        dt = datetime.strptime(date_str, "%Y%m%d")
        return (dt - timedelta(days=days)).strftime("%Y%m%d")

    start = _subtract_days(trade_date, 300)

    daily = tushare_client.get_daily(ts_code=ts_code, start_date=start, end_date=trade_date)
    if daily["status"] == "ok":
        data["daily"] = daily["data"][:60]

    daily_basic = tushare_client.get_daily_basic(ts_code=ts_code, start_date=start, end_date=trade_date)
    if daily_basic["status"] == "ok":
        data["daily_basic"] = daily_basic["data"][:60]

    adj = tushare_client.get_adj_factor(ts_code=ts_code, start_date=start, end_date=trade_date)
    if adj["status"] == "ok":
        data["adj_factor"] = adj["data"][:60]

    return data


def tech_node(state: MarketState) -> dict:
    """LangGraph 节点函数：技术面分析。"""
    ts_code = state["ts_code"]
    trade_date = state["trade_date"]
    stock_name = state.get("stock_name", ts_code)

    data = _fetch_data(ts_code, trade_date)

    system_prompt = _load_prompt()
    user_message = (
        f"请分析 {stock_name}（{ts_code}）截至 {trade_date} 的技术面。\n\n"
        f"以下是数据：\n{json.dumps(data, ensure_ascii=False, default=str)}"
    )

    tier = get_tier_config("tech")
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
            "pattern": "解析失败",
            "support": 0.0,
            "resistance": 0.0,
            "data_sources": list(data.keys()),
            "summary": content[:500],
        }

    return {"technical_score": result}
