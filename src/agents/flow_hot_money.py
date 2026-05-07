"""Flow Hot Money Agent — 游资跟踪分析节点。"""
from __future__ import annotations

import json
from pathlib import Path

from agents.state import MarketState
from sandboxes.data import tushare_client
from llm_clients.tier_router import get_tier_config
from tools.agent_tools import TOOL_MATCH_HOT_MONEY, match_hot_money
from tools.tool_executor import run_agent_with_tools


_PROMPT_PATH = Path(__file__).parent / "prompts" / "flow_hot_money.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _fetch_data(ts_code: str, trade_date: str) -> dict:
    """拉取游资跟踪分析需要的全部数据。"""
    data = {}

    top_list = tushare_client.get_top_list(trade_date=trade_date)
    if top_list["status"] == "ok":
        data["top_list"] = [r for r in top_list["data"] if r.get("ts_code") == ts_code][:20]

    block_trade = tushare_client.get_block_trade(trade_date=trade_date)
    if block_trade["status"] == "ok":
        data["block_trade"] = block_trade["data"][:10]

    try:
        top_inst = tushare_client.get_top_inst(trade_date=trade_date)
        if top_inst["status"] == "ok":
            data["top_inst"] = top_inst["data"][:20]
    except Exception:
        pass

    try:
        stk_surv = tushare_client.get_stk_surv(ts_code=ts_code)
        if stk_surv["status"] == "ok":
            data["stk_surv"] = stk_surv["data"][:10]
    except Exception:
        pass

    try:
        hm_list = tushare_client.get_hm_list()
        if hm_list["status"] == "ok":
            data["hm_list"] = hm_list["data"][:50]
    except Exception:
        pass

    return data


def flow_hot_node(state: MarketState) -> dict:
    """LangGraph 节点函数：游资跟踪分析。"""
    ts_code = state["ts_code"]
    trade_date = state["trade_date"]
    stock_name = state.get("stock_name", ts_code)

    data = _fetch_data(ts_code, trade_date)

    system_prompt = _load_prompt()
    user_message = (
        f"请分析 {stock_name}（{ts_code}）截至 {trade_date} 的游资动向。\n\n"
        f"以下是数据：\n{json.dumps(data, ensure_ascii=False, default=str)}"
    )

    tier = get_tier_config("flow_hot")
    tools = [TOOL_MATCH_HOT_MONEY]
    tool_funcs = {"match_hot_money": match_hot_money}

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
            "hot_money_trades": [],
            "data_sources": list(data.keys()),
            "summary": content[:500],
        }

    return {"flow_hot_money": result}
