"""Tests for agents.fund — mock Kimi + mock tushare。"""
from unittest.mock import patch, MagicMock
import json

import pytest

from agents.fund import fund_node, _fetch_data


@patch("agents.fund.tushare_client")
def test_fetch_data(mock_ts):
    """验证 _fetch_data 调用正确的接口。"""
    mock_ts.get_income.return_value = {"status": "ok", "data": [{"revenue": 1000}]}
    mock_ts.get_balancesheet.return_value = {"status": "ok", "data": []}
    mock_ts.get_cashflow.return_value = {"status": "ok", "data": []}
    mock_ts.get_fina_indicator.return_value = {"status": "ok", "data": []}
    mock_ts.get_forecast.return_value = {"status": "ok", "data": []}
    mock_ts.get_daily_basic.return_value = {"status": "ok", "data": []}

    data = _fetch_data("000988.SZ", "20260430")
    assert "income" in data
    mock_ts.get_income.assert_called_once()


@patch("agents.fund.call_kimi")
@patch("agents.fund.tushare_client")
def test_fund_node_success(mock_ts, mock_kimi):
    """验证 fund_node 正常流程。"""
    for attr in [
        "get_income", "get_balancesheet", "get_cashflow",
        "get_fina_indicator", "get_forecast", "get_daily_basic",
    ]:
        getattr(mock_ts, attr).return_value = {"status": "ok", "data": [{"test": 1}]}

    mock_kimi.return_value = {
        "content": json.dumps({
            "score": 75,
            "highlights": ["营收增长"],
            "risks": ["应收账款高"],
            "data_sources": ["income"],
            "summary": "基本面良好",
        }),
        "reasoning_content": None,
        "tool_calls": None,
        "usage": MagicMock(),
    }

    state = {"ts_code": "000988.SZ", "trade_date": "20260430", "stock_name": "华工科技"}
    result = fund_node(state)

    assert "fundamental_score" in result
    assert result["fundamental_score"]["score"] == 75


@patch("agents.fund.call_kimi")
@patch("agents.fund.tushare_client")
def test_fund_node_llm_parse_failure(mock_ts, mock_kimi):
    """验证 LLM 输出非 JSON 时的降级处理。"""
    for attr in [
        "get_income", "get_balancesheet", "get_cashflow",
        "get_fina_indicator", "get_forecast", "get_daily_basic",
    ]:
        getattr(mock_ts, attr).return_value = {"status": "ok", "data": []}

    mock_kimi.return_value = {
        "content": "这不是一个 JSON 格式的响应",
        "reasoning_content": None,
        "tool_calls": None,
        "usage": MagicMock(),
    }

    state = {"ts_code": "000988.SZ", "trade_date": "20260430"}
    result = fund_node(state)

    assert result["fundamental_score"]["score"] == 50
    assert "LLM 输出解析失败" in result["fundamental_score"]["risks"]
