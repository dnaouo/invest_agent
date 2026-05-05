"""Macro/Theme Agent — 宏观主题分析节点。"""
from __future__ import annotations

import json
from pathlib import Path

from agents.state import MarketState
from sandboxes.data import tushare_client, akshare_client
from llm_clients.kimi_sync import call_kimi
from llm_clients.tier_router import get_tier_config


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
            "top_themes": [],
            "policy_alerts": ["LLM 输出解析失败"],
            "data_sources": list(data.keys()),
            "summary": content[:500],
        }

    return {"macro_themes": result}
