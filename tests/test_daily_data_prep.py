"""Tests for harness/daily_data_prep.py"""
from unittest.mock import patch, MagicMock
import pytest

from sandboxes.data import duckdb_store


@pytest.fixture(autouse=True)
def _clean_duckdb():
    yield
    duckdb_store._connections.clear()


@patch("harness.daily_data_prep.akshare_client")
@patch("harness.daily_data_prep.tushare_client")
def test_run_daily_prep(mock_ts, mock_ak):
    """Mock 所有 tushare/akshare 调用，验证 stats 返回各表行数。"""
    mock_ts.get_research_report.return_value = {
        "status": "ok",
        "data": [{"title": "报告A", "report_date": "20260506", "abstr": "摘要"}],
    }
    mock_ts.get_npr.return_value = {
        "status": "ok",
        "data": [{"title": "政策A", "pub_date": "20260501", "org": "国务院"}],
    }
    mock_ts.get_hm_list.return_value = {
        "status": "ok",
        "data": [{"hm_name": "赵老哥", "broker": "华泰证券"}],
    }
    mock_ts.get_top_list.return_value = {
        "status": "ok",
        "data": [{"ts_code": "000001.SZ", "trade_date": "20260506", "exalter": "华泰", "buy": 1000, "sell": 0}],
    }
    mock_ts.get_top_inst.return_value = {
        "status": "ok",
        "data": [{"ts_code": "000001.SZ", "trade_date": "20260506", "buy": 500}],
    }
    mock_ts.get_moneyflow_ind_ths.return_value = {
        "status": "ok",
        "data": [{"ts_code": "IND001", "trade_date": "20260506", "net_amount": 100}],
    }
    mock_ts.get_moneyflow_cnt_ths.return_value = {
        "status": "ok",
        "data": [{"ts_code": "CNT001", "trade_date": "20260506", "net_amount": 50}],
    }
    mock_ts.get_limit_list_d.return_value = {
        "status": "ok",
        "data": [{"ts_code": "000002.SZ", "trade_date": "20260506", "limit": "U"}],
    }
    mock_ts.get_ths_index.return_value = {
        "status": "ok",
        "data": [{"ts_code": "THS001", "name": "光模块"}],
    }
    mock_ak.get_cls_news.return_value = {
        "status": "ok",
        "data": [{"title": "快讯1", "time": "10:00"}],
    }
    mock_ak.get_jin10_news.return_value = {
        "status": "ok",
        "data": [{"title": "金十1", "time": "11:00"}],
    }

    from harness.daily_data_prep import run_daily_prep

    stats = run_daily_prep("20260506", db_path=":memory:")

    assert "research_report" in stats
    assert stats["research_report"] == 7  # 7 天 x 1条/天
    assert "policy" in stats
    assert stats["policy"] == 1
    assert "hm_list" in stats
    assert stats["hm_list"] == 1
    assert "top_list" in stats
    assert stats["top_list"] == 1
    assert "top_inst" in stats
    assert stats["top_inst"] == 1
    assert "moneyflow_ind_ths" in stats
    assert stats["moneyflow_ind_ths"] == 1
    assert "moneyflow_cnt_ths" in stats
    assert stats["moneyflow_cnt_ths"] == 1
    assert "news_cls" in stats
    assert stats["news_cls"] == 1
    assert "news_jin10" in stats
    assert stats["news_jin10"] == 1
    assert "limit_list" in stats
    assert stats["limit_list"] == 1
    assert "ths_index" in stats
    assert stats["ths_index"] == 1
