"""Flow Institutional Agent — 机构资金分析节点。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from agents.state import MarketState
from sandboxes.data import tushare_client, akshare_client
from llm_clients.tier_router import get_tier_config
from tools.agent_tools import TOOL_GET_NORTH, get_north_individual
from tools.tool_executor import run_agent_with_tools


_PROMPT_PATH = Path(__file__).parent / "prompts" / "flow_institutional.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _fetch_data(ts_code: str, trade_date: str) -> dict:
    """拉取机构资金分析需要的全部数据。"""
    data = {}

    def _subtract_days(date_str: str, days: int) -> str:
        dt = datetime.strptime(date_str, "%Y%m%d")
        return (dt - timedelta(days=days)).strftime("%Y%m%d")

    start = _subtract_days(trade_date, 30)

    hsgt = tushare_client.get_moneyflow_hsgt(
        start_date=start, end_date=trade_date,
    )
    if hsgt["status"] == "ok":
        data["moneyflow_hsgt"] = hsgt["data"][:10]

    try:
        symbol = ts_code.replace(".SZ", "").replace(".SH", "")
        north_individual = akshare_client.get_north_flow_individual(symbol=symbol)
        if north_individual["status"] == "ok":
            data["north_individual"] = north_individual["data"][:10]
    except Exception:
        pass

    try:
        moneyflow = tushare_client.get_moneyflow(ts_code=ts_code, trade_date=trade_date)
        if moneyflow["status"] == "ok":
            data["moneyflow"] = moneyflow["data"][:5]
    except Exception:
        pass

    try:
        margin_start = _subtract_days(trade_date, 100)
        margin = tushare_client.get_margin_detail(ts_code=ts_code, start_date=margin_start, end_date=trade_date)
        if margin["status"] == "ok":
            data["margin_detail"] = margin["data"][:10]
    except Exception:
        pass

    try:
        hsgt_top = tushare_client.get_hsgt_top10(trade_date=trade_date)
        if hsgt_top["status"] == "ok":
            data["hsgt_top10"] = [r for r in hsgt_top["data"] if r.get("ts_code") == ts_code]
    except Exception:
        pass

    try:
        year = trade_date[:4]
        holders = tushare_client.get_top10_holders(ts_code=ts_code, period=f"{int(year)-1}1231")
        if holders["status"] == "ok":
            data["top10_holders"] = holders["data"][:10]
    except Exception:
        pass

    return data


def flow_inst_node(state: MarketState) -> dict:
    """LangGraph 节点函数：机构资金分析。"""
    ts_code = state["ts_code"]
    trade_date = state["trade_date"]
    stock_name = state.get("stock_name", ts_code)

    data = _fetch_data(ts_code, trade_date)

    system_prompt = _load_prompt()
    user_message = (
        f"请分析 {stock_name}（{ts_code}）截至 {trade_date} 的机构资金动向。\n\n"
        f"以下是数据：\n{json.dumps(data, ensure_ascii=False, default=str)}"
    )

    tier = get_tier_config("flow_inst")
    tools = [TOOL_GET_NORTH]
    tool_funcs = {"get_north_individual": get_north_individual}

    response = run_agent_with_tools(
        system_prompt=system_prompt,
        user_message=user_message,
        tools=tools,
        tool_functions=tool_funcs,
        tier_config=tier,
        max_rounds=3,
    )

    content = response["content"]
    try:
        start_idx = content.index("{")
        end_idx = content.rindex("}") + 1
        result = json.loads(content[start_idx:end_idx])
    except (ValueError, json.JSONDecodeError):
        result = {
            "score": 50,
            "north_flow_trend": "未知",
            "margin_signal": "未知",
            "data_sources": list(data.keys()),
            "summary": content[:500],
        }

    return {"flow_institutional": result}
