"""Tests for tushare_client extended functions — all mocked, no real API calls."""

from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

import sandboxes.data.tushare_client as client


@pytest.fixture(autouse=True)
def _reset_pro():
    """每个测试前重置懒加载的 _pro 实例。"""
    client._pro = None
    yield
    client._pro = None


# ---------------------------------------------------------------------------
# Fundamental Agent
# ---------------------------------------------------------------------------


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_balancesheet_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.balancesheet.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "total_assets": 5000000.0},
    ])

    result = client.get_balancesheet("000001.SZ", "20261231")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["total_assets"] == 5000000.0
    mock_pro.balancesheet.assert_called_once_with(ts_code="000001.SZ", period="20261231")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_cashflow_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.cashflow.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "net_cashflow_oper_act": 800000.0},
    ])

    result = client.get_cashflow("000001.SZ", "20261231")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["net_cashflow_oper_act"] == 800000.0
    mock_pro.cashflow.assert_called_once_with(ts_code="000001.SZ", period="20261231")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_fina_indicator_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.fina_indicator.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "roe": 15.5},
    ])

    result = client.get_fina_indicator("000001.SZ", "20261231")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["roe"] == 15.5
    mock_pro.fina_indicator.assert_called_once_with(ts_code="000001.SZ", period="20261231")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_forecast_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.forecast.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "type": "预增"},
    ])

    result = client.get_forecast("000001.SZ")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["type"] == "预增"
    mock_pro.forecast.assert_called_once_with(ts_code="000001.SZ")


# ---------------------------------------------------------------------------
# Technical Agent
# ---------------------------------------------------------------------------


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_daily_basic_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.daily_basic.return_value = pd.DataFrame([
        {"trade_date": "20260502", "turnover_rate": 3.5, "pe": 12.0},
    ])

    result = client.get_daily_basic("000001.SZ", "20260101", "20260502")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["pe"] == 12.0
    mock_pro.daily_basic.assert_called_once_with(
        ts_code="000001.SZ", start_date="20260101", end_date="20260502"
    )


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_adj_factor_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.adj_factor.return_value = pd.DataFrame([
        {"trade_date": "20260502", "adj_factor": 120.5},
    ])

    result = client.get_adj_factor("000001.SZ", "20260101", "20260502")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["adj_factor"] == 120.5
    mock_pro.adj_factor.assert_called_once_with(
        ts_code="000001.SZ", start_date="20260101", end_date="20260502"
    )


# ---------------------------------------------------------------------------
# Event Agent
# ---------------------------------------------------------------------------


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_share_float_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.share_float.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "float_date": "20260601", "float_share": 10000.0},
    ])

    result = client.get_share_float("000001.SZ")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["float_share"] == 10000.0
    mock_pro.share_float.assert_called_once_with(ts_code="000001.SZ")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_stk_holdertrade_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.stk_holdertrade.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "holder_name": "张三", "vol": 50000.0},
    ])

    result = client.get_stk_holdertrade("000001.SZ", "20260101", "20260502")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["holder_name"] == "张三"
    mock_pro.stk_holdertrade.assert_called_once_with(
        ts_code="000001.SZ", start_date="20260101", end_date="20260502"
    )


# ---------------------------------------------------------------------------
# Flow Hot Money Agent
# ---------------------------------------------------------------------------


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_top_list_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.top_list.return_value = pd.DataFrame([
        {"trade_date": "20260502", "ts_code": "000001.SZ", "buy": 100000.0},
    ])

    result = client.get_top_list("20260502")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["buy"] == 100000.0
    mock_pro.top_list.assert_called_once_with(trade_date="20260502")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_top_inst_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.top_inst.return_value = pd.DataFrame([
        {"trade_date": "20260502", "exalter": "机构A", "buy": 200000.0},
    ])

    result = client.get_top_inst("20260502")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["exalter"] == "机构A"
    mock_pro.top_inst.assert_called_once_with(trade_date="20260502")


# ---------------------------------------------------------------------------
# Flow Institutional Agent
# ---------------------------------------------------------------------------


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_moneyflow_hsgt_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.moneyflow_hsgt.return_value = pd.DataFrame([
        {"trade_date": "20260502", "north_money": 5000000.0},
    ])

    result = client.get_moneyflow_hsgt("20260101", "20260502")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["north_money"] == 5000000.0
    mock_pro.moneyflow_hsgt.assert_called_once_with(
        start_date="20260101", end_date="20260502"
    )


# ---------------------------------------------------------------------------
# Risk Agent
# ---------------------------------------------------------------------------


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_pledge_stat_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.pledge_stat.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "pledge_count": 5, "pledge_ratio": 10.2},
    ])

    result = client.get_pledge_stat("000001.SZ")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["pledge_ratio"] == 10.2
    mock_pro.pledge_stat.assert_called_once_with(ts_code="000001.SZ")
