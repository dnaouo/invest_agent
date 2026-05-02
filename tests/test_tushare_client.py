"""Tests for sandboxes.data.tushare_client — all mocked, no real API calls."""

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
def test_get_daily_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.daily.return_value = pd.DataFrame([
        {"trade_date": "20260502", "open": 10.5, "close": 11.0},
    ])

    result = client.get_daily("000001.SZ", "20260101", "20260502")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["trade_date"] == "20260502"
    mock_pro.daily.assert_called_once_with(
        ts_code="000001.SZ", start_date="20260101", end_date="20260502"
    )


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_daily_api_error(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.daily.side_effect = RuntimeError("接口频率限制")

    result = client.get_daily("000001.SZ", "20260101", "20260502")

    assert result["status"] == "error"
    assert result["error_code"] == "TUSHARE_API_ERROR"
    assert "接口频率限制" in result["message"]
    assert result["retry_hint"] is False


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_income_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.income.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "ann_date": "20260401", "revenue": 1000000.0},
    ])

    result = client.get_income("000001.SZ", "20261231")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["ts_code"] == "000001.SZ"
    mock_pro.income.assert_called_once_with(ts_code="000001.SZ", period="20261231")
