"""Tests for Macro / Tech / Event agents — mock Kimi + mock data clients."""
from unittest.mock import patch, MagicMock
import json

import pytest

from agents.macro import macro_node
from agents.tech import tech_node
from agents.event import event_node


# ─── Macro Agent ────────────────────────────────────────────────────────────


@patch("agents.macro.run_agent_with_tools")
@patch("agents.macro.akshare_client")
@patch("agents.macro.tushare_client")
def test_macro_node(mock_ts, mock_ak, mock_run):
    """验证 macro_node 返回正确的 state key 并解析 JSON。"""
    mock_ts.get_ths_index.return_value = {
        "status": "ok",
        "data": [{"name": "CPO", "pct_change": 5.2}],
    }
    mock_ak.get_cls_news.return_value = {
        "status": "ok",
        "data": [{"title": "算力政策"}],
    }
    mock_ak.get_jin10_news.return_value = {
        "status": "ok",
        "data": [{"content": "美联储维持利率"}],
    }

    mock_ts.get_moneyflow_ind_ths.return_value = {
        "status": "ok",
        "data": [{"test": 1}],
    }
    mock_ts.get_moneyflow_cnt_ths.return_value = {
        "status": "ok",
        "data": [{"test": 1}],
    }
    mock_ts.get_npr.return_value = {
        "status": "ok",
        "data": [{"test": 1}],
    }

    mock_run.return_value = {
        "content": json.dumps({
            "score": 82,
            "top_themes": [{"name": "CPO", "score": 88, "trend": "上升"}],
            "policy_alerts": ["算力政策发布"],
            "data_sources": ["ths_index", "cls_news"],
            "summary": "主线明确",
        }),
        "reasoning_content": None,
        "tool_calls_made": [],
    }

    state = {"ts_code": "000988.SZ", "trade_date": "20260430", "stock_name": "华工科技"}
    result = macro_node(state)

    assert "macro_themes" in result
    assert result["macro_themes"]["score"] == 82
    assert len(result["macro_themes"]["top_themes"]) == 1


# ─── Technical Agent ────────────────────────────────────────────────────────


@patch("agents.tech.call_kimi")
@patch("agents.tech.tushare_client")
def test_tech_node(mock_ts, mock_kimi):
    """验证 tech_node 返回正确的 state key 并解析 JSON。"""
    mock_ts.get_daily.return_value = {
        "status": "ok",
        "data": [{"close": 48.3, "vol": 120000}],
    }
    mock_ts.get_daily_basic.return_value = {
        "status": "ok",
        "data": [{"pe_ttm": 32.5, "turnover_rate": 6.2}],
    }
    mock_ts.get_adj_factor.return_value = {
        "status": "ok",
        "data": [{"adj_factor": 1.05}],
    }

    mock_kimi.return_value = {
        "content": json.dumps({
            "score": 76,
            "pattern": "上升通道放量突破",
            "support": 44.12,
            "resistance": 50.0,
            "data_sources": ["daily", "daily_basic", "adj_factor"],
            "summary": "技术面偏多",
        }),
        "reasoning_content": None,
        "tool_calls": None,
        "usage": MagicMock(),
    }

    state = {"ts_code": "000988.SZ", "trade_date": "20260430", "stock_name": "华工科技"}
    result = tech_node(state)

    assert "technical_score" in result
    assert result["technical_score"]["score"] == 76
    assert result["technical_score"]["pattern"] == "上升通道放量突破"


# ─── Event Agent ────────────────────────────────────────────────────────────


@patch("agents.event.run_agent_with_tools")
@patch("agents.event.tushare_client")
def test_event_node(mock_ts, mock_run):
    """验证 event_node 返回正确的 state key 并解析 JSON。"""
    mock_ts.get_anns_d.return_value = {
        "status": "ok",
        "data": [{"title": "业绩预告"}],
    }
    mock_ts.get_share_float.return_value = {
        "status": "ok",
        "data": [{"float_share": 1200}],
    }
    mock_ts.get_stk_holdertrade.return_value = {
        "status": "ok",
        "data": [{"holder_name": "张三", "vol": 500}],
    }
    mock_ts.get_forecast.return_value = {
        "status": "ok",
        "data": [{"type": "预增", "p_change_min": 50, "p_change_max": 80}],
    }
    mock_ts.get_research_report.return_value = {
        "status": "ok",
        "data": [{"test": 1}],
    }

    mock_run.return_value = {
        "content": json.dumps({
            "score": 78,
            "events": [
                {"type": "earnings_beat", "strength": 0.85, "detail": "预增50-80%"}
            ],
            "data_sources": ["forecast", "stk_holdertrade"],
            "summary": "事件面偏正面",
        }),
        "reasoning_content": None,
        "tool_calls_made": [],
    }

    state = {"ts_code": "000988.SZ", "trade_date": "20260430", "stock_name": "华工科技"}
    result = event_node(state)

    assert "event_analysis" in result
    assert result["event_analysis"]["score"] == 78
    assert result["event_analysis"]["events"][0]["type"] == "earnings_beat"
