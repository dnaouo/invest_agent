"""Tests for batch 2 agents — flow_institutional, flow_hot_money, risk, backtest."""
from unittest.mock import patch, MagicMock
import json

import pytest

from agents.flow_institutional import flow_inst_node, _fetch_data as fi_fetch
from agents.flow_hot_money import flow_hot_node, _fetch_data as fh_fetch
from agents.risk import risk_node, _fetch_data as risk_fetch
from agents.backtest import backtest_node, _fetch_data as bt_fetch


# ---------- Flow Institutional ----------

@patch("agents.flow_institutional.run_agent_with_tools")
@patch("agents.flow_institutional.akshare_client")
@patch("agents.flow_institutional.tushare_client")
def test_flow_inst_node(mock_ts, mock_ak, mock_run):
    """验证 flow_inst_node 正常流程。"""
    mock_ts.get_moneyflow_hsgt.return_value = {
        "status": "ok",
        "data": [{"trade_date": "20260430", "north_money": 12.3}],
    }
    mock_ak.get_north_flow_individual.return_value = {
        "status": "ok",
        "data": [{"test": 1}],
    }
    mock_ts.get_moneyflow.return_value = {
        "status": "ok",
        "data": [{"test": 1}],
    }
    mock_ts.get_margin_detail.return_value = {
        "status": "ok",
        "data": [{"test": 1}],
    }
    mock_ts.get_hsgt_top10.return_value = {
        "status": "ok",
        "data": [{"test": 1}],
    }
    mock_ts.get_top10_holders.return_value = {
        "status": "ok",
        "data": [{"test": 1}],
    }

    mock_run.return_value = {
        "content": json.dumps({
            "score": 72,
            "north_flow_trend": "持续流入",
            "margin_signal": "融资增加",
            "data_sources": ["moneyflow_hsgt_20260430"],
            "summary": "北向资金持续流入",
        }),
        "reasoning_content": None,
        "tool_calls_made": [],
    }

    state = {"ts_code": "000988.SZ", "trade_date": "20260430", "stock_name": "华工科技"}
    result = flow_inst_node(state)

    assert "flow_institutional" in result
    assert result["flow_institutional"]["score"] == 72
    mock_ts.get_moneyflow_hsgt.assert_called_once()


# ---------- Flow Hot Money ----------

@patch("agents.flow_hot_money.run_agent_with_tools")
@patch("agents.flow_hot_money.tushare_client")
def test_flow_hot_node(mock_ts, mock_run):
    """验证 flow_hot_node 正常流程。"""
    mock_ts.get_top_list.return_value = {
        "status": "ok",
        "data": [{"buy_amount": 8500, "sell_amount": 3200}],
    }
    mock_ts.get_block_trade.return_value = {
        "status": "ok",
        "data": [{"price": 25.3, "premium": -2.1}],
    }
    mock_ts.get_top_inst.return_value = {
        "status": "ok",
        "data": [{"test": 1}],
    }
    mock_ts.get_stk_surv.return_value = {
        "status": "ok",
        "data": [{"test": 1}],
    }
    mock_ts.get_hm_list.return_value = {
        "status": "ok",
        "data": [{"test": 1}],
    }

    mock_run.return_value = {
        "content": json.dumps({
            "score": 65,
            "hot_money_trades": [
                {"trader": "东方财富拉萨团结路", "action": "买入", "amount": 0.85}
            ],
            "data_sources": ["top_list_20260430", "block_trade_20260430"],
            "summary": "游资关注，信号中性偏多",
        }),
        "reasoning_content": None,
        "tool_calls_made": [],
    }

    state = {"ts_code": "000988.SZ", "trade_date": "20260430", "stock_name": "华工科技"}
    result = flow_hot_node(state)

    assert "flow_hot_money" in result
    assert result["flow_hot_money"]["score"] == 65
    mock_ts.get_top_list.assert_called_once()
    mock_ts.get_block_trade.assert_called_once()


# ---------- Risk ----------

@patch("agents.risk.call_kimi")
@patch("agents.risk.tushare_client")
def test_risk_node(mock_ts, mock_kimi):
    """验证 risk_node 正常流程。"""
    mock_ts.get_pledge_stat.return_value = {
        "status": "ok",
        "data": [{"pledge_ratio": 15.3}],
    }
    mock_ts.get_stk_holdertrade.return_value = {
        "status": "ok",
        "data": [{"holder_name": "张三", "change_vol": -500000}],
    }
    mock_ts.get_share_float.return_value = {
        "status": "ok",
        "data": [],
    }

    mock_kimi.return_value = {
        "content": json.dumps({
            "score": 82,
            "risk_flags": [],
            "position_suggestion": {"max_pct": 12.0, "stop_loss": 24.8},
            "data_sources": ["pledge_stat_000988", "stk_holdertrade"],
            "summary": "风险可控",
        }),
        "reasoning_content": None,
        "tool_calls": None,
        "usage": MagicMock(),
    }

    state = {"ts_code": "000988.SZ", "trade_date": "20260430", "stock_name": "华工科技"}
    result = risk_node(state)

    assert "risk_assessment" in result
    assert result["risk_assessment"]["score"] == 82
    mock_ts.get_pledge_stat.assert_called_once()
    mock_ts.get_stk_holdertrade.assert_called_once()
    mock_ts.get_share_float.assert_called_once()


# ---------- Backtest ----------

@patch("agents.backtest.call_kimi")
@patch("agents.backtest.tushare_client")
def test_backtest_node(mock_ts, mock_kimi):
    """验证 backtest_node 正常流程。"""
    mock_ts.get_daily.return_value = {
        "status": "ok",
        "data": [{"close": 26.5, "vol": 120000} for _ in range(5)],
    }
    mock_ts.get_daily_basic.return_value = {
        "status": "ok",
        "data": [{"pe": 28.5, "turnover_rate": 3.2} for _ in range(5)],
    }

    mock_kimi.return_value = {
        "content": json.dumps({
            "score": 71,
            "sharpe": 1.25,
            "max_drawdown": -0.153,
            "win_rate": 0.62,
            "similar_cases": [
                {"date": "20250315", "return_20d": 0.12, "pattern": "放量突破"}
            ],
            "data_sources": ["daily_000988_120d", "daily_basic_000988_120d"],
            "summary": "回测支持买入信号",
        }),
        "reasoning_content": None,
        "tool_calls": None,
        "usage": MagicMock(),
    }

    state = {"ts_code": "000988.SZ", "trade_date": "20260430", "stock_name": "华工科技"}
    result = backtest_node(state)

    assert "backtest_result" in result
    assert result["backtest_result"]["score"] == 71
    assert result["backtest_result"]["sharpe"] == 1.25
    mock_ts.get_daily.assert_called_once()
    mock_ts.get_daily_basic.assert_called_once()
