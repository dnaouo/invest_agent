"""Fundamental Agent — 基本面分析节点。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from agents.state import MarketState
from sandboxes.data import tushare_client
from llm_clients.tier_router import get_tier_config
from tools.agent_tools import TOOL_SEARCH_REPORTS, TOOL_CLASSIFY_EVENTS, search_reports, classify_events
from tools.tool_executor import run_agent_with_tools


_PROMPT_PATH = Path(__file__).parent / "prompts" / "fundamental.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _fetch_data(ts_code: str, trade_date: str) -> dict:
    """拉取基本面分析需要的全部数据。"""
    data = {}

    year = trade_date[:4]
    period = f"{int(year)-1}1231"

    for name, func in [
        ("income", tushare_client.get_income),
        ("balancesheet", tushare_client.get_balancesheet),
        ("cashflow", tushare_client.get_cashflow),
        ("fina_indicator", tushare_client.get_fina_indicator),
    ]:
        result = func(ts_code=ts_code, period=period)
        if result["status"] == "ok":
            data[name] = result["data"]

    forecast = tushare_client.get_forecast(ts_code=ts_code)
    if forecast["status"] == "ok":
        data["forecast"] = forecast["data"][:5]

    def _subtract_days(date_str: str, days: int) -> str:
        dt = datetime.strptime(date_str, "%Y%m%d")
        return (dt - timedelta(days=days)).strftime("%Y%m%d")

    start = _subtract_days(trade_date, 100)
    daily_basic = tushare_client.get_daily_basic(
        ts_code=ts_code, start_date=start, end_date=trade_date,
    )
    if daily_basic["status"] == "ok":
        data["daily_basic"] = daily_basic["data"][:5]

    try:
        mainbz = tushare_client.get_fina_mainbz(ts_code=ts_code, period=period)
        if mainbz["status"] == "ok":
            data["fina_mainbz"] = mainbz["data"]
    except Exception:
        pass

    try:
        holdernumber = tushare_client.get_stk_holdernumber(ts_code=ts_code, end_date=trade_date)
        if holdernumber["status"] == "ok":
            data["stk_holdernumber"] = holdernumber["data"][:8]
    except Exception:
        pass

    try:
        research = tushare_client.get_research_report(trade_date)
        if research["status"] == "ok":
            relevant = [r for r in research["data"] if ts_code[:6] in str(r.get("title", "")) or ts_code[:6] in str(r.get("abstr", ""))]
            if relevant:
                data["research_reports"] = relevant[:5]
    except Exception:
        pass

    try:
        stk_surv = tushare_client.get_stk_surv(ts_code=ts_code)
        if stk_surv["status"] == "ok":
            data["stk_surv"] = stk_surv["data"][:10]
    except Exception:
        pass

    try:
        moneyflow = tushare_client.get_moneyflow(ts_code=ts_code, trade_date=trade_date)
        if moneyflow["status"] == "ok":
            data["moneyflow"] = moneyflow["data"][:5]
    except Exception:
        pass

    return data


def fund_node(state: MarketState) -> dict:
    """LangGraph 节点函数：基本面分析。"""
    ts_code = state["ts_code"]
    trade_date = state["trade_date"]
    stock_name = state.get("stock_name", ts_code)

    data = _fetch_data(ts_code, trade_date)

    system_prompt = _load_prompt()
    user_message = (
        f"请分析 {stock_name}（{ts_code}）截至 {trade_date} 的基本面。\n\n"
        f"以下是数据：\n{json.dumps(data, ensure_ascii=False, default=str)}"
    )

    tier = get_tier_config("fund")
    tools = [TOOL_SEARCH_REPORTS, TOOL_CLASSIFY_EVENTS]
    tool_funcs = {"search_reports": search_reports, "classify_events": classify_events}

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
            "highlights": [],
            "risks": ["LLM 输出解析失败"],
            "data_sources": list(data.keys()),
            "summary": content[:500],
        }

    return {"fundamental_score": result}
