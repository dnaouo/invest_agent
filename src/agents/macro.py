"""Macro/Theme Agent — 宏观主题分析节点。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from agents.state import MarketState
from sandboxes.data import tushare_client, akshare_client
from llm_clients.tier_router import get_tier_config
from tools.agent_tools import (
    TOOL_SEARCH_POLICY, TOOL_SEARCH_NEWS, TOOL_GET_THEME,
    search_policy, search_news, get_theme_members,
)
from tools.tool_executor import run_agent_with_tools


_PROMPT_PATH = Path(__file__).parent / "prompts" / "macro.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _fetch_data(trade_date: str) -> dict:
    """拉取宏观主题分析需要的全部数据。"""
    data = {}

    ths = tushare_client.get_ths_index()
    if ths["status"] == "ok":
        data["ths_index"] = ths["data"][:30]

    cls_news = akshare_client.get_cls_news(count=50)
    if cls_news["status"] == "ok":
        data["cls_news"] = cls_news["data"][:20]

    jin10 = akshare_client.get_jin10_news(count=50)
    if jin10["status"] == "ok":
        data["jin10_news"] = jin10["data"][:20]

    try:
        ind_flow = tushare_client.get_moneyflow_ind_ths(trade_date=trade_date)
        if ind_flow["status"] == "ok":
            data["industry_moneyflow"] = ind_flow["data"][:20]
    except Exception:
        pass

    try:
        cnt_flow = tushare_client.get_moneyflow_cnt_ths(trade_date=trade_date)
        if cnt_flow["status"] == "ok":
            data["concept_moneyflow"] = cnt_flow["data"][:20]
    except Exception:
        pass

    try:
        def _subtract_days(date_str: str, days: int) -> str:
            dt = datetime.strptime(date_str, "%Y%m%d")
            return (dt - timedelta(days=days)).strftime("%Y%m%d")

        start_date = _subtract_days(trade_date, 30)
        npr_result = tushare_client.get_npr(start_date=start_date, end_date=trade_date)
        if npr_result["status"] == "ok":
            data["policies"] = npr_result["data"][:10]
    except Exception:
        pass

    return data


def macro_node(state: MarketState) -> dict:
    """LangGraph 节点函数：宏观主题分析。"""
    trade_date = state["trade_date"]

    data = _fetch_data(trade_date)

    system_prompt = _load_prompt()
    user_message = (
        f"请分析截至 {trade_date} 的宏观主题格局。\n\n"
        f"以下是数据：\n{json.dumps(data, ensure_ascii=False, default=str)}"
    )

    tier = get_tier_config("macro")
    tools = [TOOL_SEARCH_POLICY, TOOL_SEARCH_NEWS, TOOL_GET_THEME]
    tool_funcs = {
        "search_policy": search_policy,
        "search_news": search_news,
        "get_theme_members": get_theme_members,
    }

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
            "top_themes": [],
            "policy_alerts": ["LLM 输出解析失败"],
            "data_sources": list(data.keys()),
            "summary": content[:500],
        }

    return {"macro_themes": result}
