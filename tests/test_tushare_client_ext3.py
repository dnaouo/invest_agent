"""Tests for tushare_client V2-A functions — all mocked, no real API calls."""

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


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_moneyflow_ind_ths_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.moneyflow_ind_ths.return_value = pd.DataFrame([
        {"ts_code": "885600.TI", "trade_date": "20260506", "net_amount": 100.5},
    ])

    result = client.get_moneyflow_ind_ths("20260506")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["net_amount"] == 100.5
    mock_pro.moneyflow_ind_ths.assert_called_once_with(trade_date="20260506")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_moneyflow_cnt_ths_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.moneyflow_cnt_ths.return_value = pd.DataFrame([
        {"ts_code": "TS001", "trade_date": "20260506", "net_amount": 50.2},
    ])

    result = client.get_moneyflow_cnt_ths("20260506")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["net_amount"] == 50.2
    mock_pro.moneyflow_cnt_ths.assert_called_once_with(trade_date="20260506")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_fina_mainbz_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.fina_mainbz.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "bz_item": "零售业务", "bz_sales": 1000.0},
    ])

    result = client.get_fina_mainbz("000001.SZ", "20251231")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["bz_item"] == "零售业务"
    mock_pro.fina_mainbz.assert_called_once_with(ts_code="000001.SZ", period="20251231")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_stk_holdernumber_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.stk_holdernumber.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "ann_date": "20260401", "holder_num": 50000},
    ])

    result = client.get_stk_holdernumber("000001.SZ", start_date="20260101", end_date="20260501")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["holder_num"] == 50000
    mock_pro.stk_holdernumber.assert_called_once_with(
        ts_code="000001.SZ", start_date="20260101", end_date="20260501"
    )


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_stk_holdernumber_no_optional_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.stk_holdernumber.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "holder_num": 50000},
    ])

    result = client.get_stk_holdernumber("000001.SZ")

    assert result["status"] == "ok"
    mock_pro.stk_holdernumber.assert_called_once_with(ts_code="000001.SZ")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_forecast_vip_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.forecast_vip.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "ann_date": "20260401", "type": "预增"},
    ])

    result = client.get_forecast_vip("20260401")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["type"] == "预增"
    mock_pro.forecast_vip.assert_called_once_with(ann_date="20260401")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_express_vip_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.express_vip.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "ann_date": "20260401", "revenue": 5000.0},
    ])

    result = client.get_express_vip("20260401")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["revenue"] == 5000.0
    mock_pro.express_vip.assert_called_once_with(ann_date="20260401")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_limit_list_d_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.limit_list_d.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "trade_date": "20260506", "limit": "U"},
    ])

    result = client.get_limit_list_d("20260506")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["limit"] == "U"
    mock_pro.limit_list_d.assert_called_once_with(trade_date="20260506")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_margin_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.margin.return_value = pd.DataFrame([
        {"trade_date": "20260506", "rzye": 10000.0, "rqye": 5000.0},
    ])

    result = client.get_margin("20260506")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["rzye"] == 10000.0
    mock_pro.margin.assert_called_once_with(trade_date="20260506")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_margin_detail_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.margin_detail.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "trade_date": "20260506", "rzye": 800.0},
    ])

    result = client.get_margin_detail("000001.SZ", start_date="20260101", end_date="20260506")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["rzye"] == 800.0
    mock_pro.margin_detail.assert_called_once_with(
        ts_code="000001.SZ", start_date="20260101", end_date="20260506"
    )


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_margin_detail_no_optional_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.margin_detail.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "rzye": 800.0},
    ])

    result = client.get_margin_detail("000001.SZ")

    assert result["status"] == "ok"
    mock_pro.margin_detail.assert_called_once_with(ts_code="000001.SZ")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_hsgt_top10_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.hsgt_top10.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "trade_date": "20260506", "net_amount": 200.0},
    ])

    result = client.get_hsgt_top10("20260506")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["net_amount"] == 200.0
    mock_pro.hsgt_top10.assert_called_once_with(trade_date="20260506")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_top10_holders_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.top10_holders.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "ann_date": "20260401", "holder_name": "中国平安"},
    ])

    result = client.get_top10_holders("000001.SZ", period="20251231")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["holder_name"] == "中国平安"
    mock_pro.top10_holders.assert_called_once_with(ts_code="000001.SZ", period="20251231")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_top10_holders_no_optional_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.top10_holders.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "holder_name": "中国平安"},
    ])

    result = client.get_top10_holders("000001.SZ")

    assert result["status"] == "ok"
    mock_pro.top10_holders.assert_called_once_with(ts_code="000001.SZ")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_moneyflow_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.moneyflow.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "trade_date": "20260506", "buy_lg_amount": 500.0},
    ])

    result = client.get_moneyflow(ts_code="000001.SZ", trade_date="20260506")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["buy_lg_amount"] == 500.0
    mock_pro.moneyflow.assert_called_once_with(ts_code="000001.SZ", trade_date="20260506")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_moneyflow_no_optional_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.moneyflow.return_value = pd.DataFrame([])

    result = client.get_moneyflow()

    assert result["status"] == "ok"
    mock_pro.moneyflow.assert_called_once_with()


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_index_daily_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.index_daily.return_value = pd.DataFrame([
        {"ts_code": "000300.SH", "trade_date": "20260506", "close": 4000.0},
    ])

    result = client.get_index_daily("000300.SH", "20260101", "20260506")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["close"] == 4000.0
    mock_pro.index_daily.assert_called_once_with(
        ts_code="000300.SH", start_date="20260101", end_date="20260506"
    )
