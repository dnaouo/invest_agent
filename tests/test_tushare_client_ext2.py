"""Tests for tushare_client ext2 functions — all mocked, no real API calls."""

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
def test_get_anns_d_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.anns_d.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "ann_date": "20260502", "title": "年度报告"},
    ])

    result = client.get_anns_d("000001.SZ", "20260101", "20260502")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["title"] == "年度报告"
    mock_pro.anns_d.assert_called_once_with(
        ts_code="000001.SZ", start_date="20260101", end_date="20260502"
    )


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_ths_index_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.ths_index.return_value = pd.DataFrame([
        {"ts_code": "885600.TI", "name": "半导体", "type": "N"},
    ])

    result = client.get_ths_index(exchange="", type="N")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["name"] == "半导体"
    mock_pro.ths_index.assert_called_once_with(exchange="", type="N")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_ths_member_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.ths_member.return_value = pd.DataFrame([
        {"ts_code": "885600.TI", "code": "000001.SZ", "name": "平安银行"},
    ])

    result = client.get_ths_member("885600.TI")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["code"] == "000001.SZ"
    mock_pro.ths_member.assert_called_once_with(ts_code="885600.TI")


@patch("sandboxes.data.tushare_client.get_credential", return_value="fake_token")
@patch("sandboxes.data.tushare_client.ts.pro_api")
def test_get_stk_surv_success(mock_pro_api, mock_cred):
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro
    mock_pro.stk_surv.return_value = pd.DataFrame([
        {"ts_code": "000001.SZ", "surv_date": "20260401", "fund_visitors": 3},
    ])

    result = client.get_stk_surv("000001.SZ")

    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["fund_visitors"] == 3
    mock_pro.stk_surv.assert_called_once_with(ts_code="000001.SZ")
