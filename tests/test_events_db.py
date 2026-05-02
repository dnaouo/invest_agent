"""事件分类标签体系测试。"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from sandboxes.data.events_db import (
    EventType,
    _classify_forecast,
    _classify_holdertrade,
    _classify_share_float,
    classify_events,
)
from sandboxes.data.duckdb_store import query, close


@pytest.fixture(autouse=True)
def _cleanup_db():
    yield
    close(":memory:")


class TestClassifyForecast:
    def test_beat(self):
        records = [
            {
                "ts_code": "000001.SZ",
                "type": "预增",
                "summary": "净利润同比增长50-80%",
                "ann_date": "20260401",
            }
        ]
        events = _classify_forecast(records)
        assert len(events) == 1
        e = events[0]
        assert e["ts_code"] == "000001.SZ"
        assert e["event_type"] == EventType.EARNINGS_BEAT.value
        assert e["strength"] == 0.9
        assert e["source"] == "forecast"
        assert "预增" in e["detail"]

    def test_beat_twist(self):
        records = [{"ts_code": "000002.SZ", "type": "扭亏", "summary": "", "ann_date": "20260401"}]
        events = _classify_forecast(records)
        assert len(events) == 1
        assert events[0]["event_type"] == EventType.EARNINGS_BEAT.value

    def test_miss(self):
        records = [
            {
                "ts_code": "000003.SZ",
                "type": "预减",
                "summary": "净利润同比下降30-50%",
                "ann_date": "20260401",
            }
        ]
        events = _classify_forecast(records)
        assert len(events) == 1
        e = events[0]
        assert e["event_type"] == EventType.EARNINGS_MISS.value
        assert e["strength"] == 0.9

    def test_miss_first_loss(self):
        records = [{"ts_code": "000004.SZ", "type": "首亏", "summary": "", "ann_date": "20260401"}]
        events = _classify_forecast(records)
        assert len(events) == 1
        assert events[0]["event_type"] == EventType.EARNINGS_MISS.value

    def test_unknown_type_skipped(self):
        records = [{"ts_code": "000005.SZ", "type": "不确定", "summary": "", "ann_date": "20260401"}]
        events = _classify_forecast(records)
        assert len(events) == 0

    def test_empty_type_skipped(self):
        records = [{"ts_code": "000006.SZ", "type": "", "summary": "", "ann_date": "20260401"}]
        events = _classify_forecast(records)
        assert len(events) == 0


class TestClassifyShareFloat:
    def test_basic(self):
        records = [
            {
                "ts_code": "000001.SZ",
                "float_date": "20260501",
                "float_share": 1000000.0,
                "ann_date": "20260401",
            }
        ]
        events = _classify_share_float(records)
        assert len(events) == 1
        e = events[0]
        assert e["event_type"] == EventType.IPO_UNLOCK.value
        assert e["strength"] == 0.7
        assert e["source"] == "share_float"
        assert e["ann_date"] == "20260501"

    def test_fallback_ann_date(self):
        records = [{"ts_code": "000001.SZ", "float_share": 500000.0, "ann_date": "20260301"}]
        events = _classify_share_float(records)
        assert events[0]["ann_date"] == "20260301"


class TestClassifyHoldertrade:
    def test_increase_by_in_de(self):
        records = [
            {
                "ts_code": "000001.SZ",
                "in_de": "IN",
                "trade_type": "竞价交易增持",
                "holder_name": "张三",
                "ann_date": "20260401",
            }
        ]
        events = _classify_holdertrade(records)
        assert len(events) == 1
        e = events[0]
        assert e["event_type"] == EventType.HOLDER_INCREASE.value
        assert e["strength"] == 0.6

    def test_decrease_by_in_de(self):
        records = [
            {
                "ts_code": "000001.SZ",
                "in_de": "DE",
                "trade_type": "竞价交易减持",
                "holder_name": "李四",
                "ann_date": "20260401",
            }
        ]
        events = _classify_holdertrade(records)
        assert len(events) == 1
        e = events[0]
        assert e["event_type"] == EventType.HOLDER_DECREASE.value
        assert e["strength"] == 0.8

    def test_increase_by_trade_type(self):
        records = [
            {
                "ts_code": "000001.SZ",
                "in_de": "",
                "trade_type": "增持",
                "holder_name": "王五",
                "ann_date": "20260401",
            }
        ]
        events = _classify_holdertrade(records)
        assert events[0]["event_type"] == EventType.HOLDER_INCREASE.value

    def test_decrease_by_trade_type(self):
        records = [
            {
                "ts_code": "000001.SZ",
                "in_de": "",
                "trade_type": "减持",
                "holder_name": "赵六",
                "ann_date": "20260401",
            }
        ]
        events = _classify_holdertrade(records)
        assert events[0]["event_type"] == EventType.HOLDER_DECREASE.value

    def test_unknown_skipped(self):
        records = [
            {
                "ts_code": "000001.SZ",
                "in_de": "",
                "trade_type": "其他",
                "holder_name": "XX",
                "ann_date": "20260401",
            }
        ]
        events = _classify_holdertrade(records)
        assert len(events) == 0


class TestClassifyEventsCombined:
    @patch("sandboxes.data.events_db.tushare_client")
    def test_combined(self, mock_tc):
        mock_tc.get_forecast.return_value = {
            "status": "ok",
            "data": [
                {"ts_code": "000988.SZ", "type": "预增", "summary": "净利润同比增长50-80%", "ann_date": "20260401"},
            ],
        }
        mock_tc.get_share_float.return_value = {
            "status": "ok",
            "data": [
                {"ts_code": "000988.SZ", "float_date": "20260501", "float_share": 1000000.0, "ann_date": "20260401"},
            ],
        }
        mock_tc.get_stk_holdertrade.return_value = {
            "status": "ok",
            "data": [
                {
                    "ts_code": "000988.SZ",
                    "in_de": "DE",
                    "trade_type": "竞价交易减持",
                    "holder_name": "大股东A",
                    "ann_date": "20260402",
                },
            ],
        }

        events = classify_events("000988.SZ", "20260101", "20260501", db_path=":memory:")

        assert len(events) == 3

        types = {e["event_type"] for e in events}
        assert types == {
            EventType.EARNINGS_BEAT.value,
            EventType.IPO_UNLOCK.value,
            EventType.HOLDER_DECREASE.value,
        }

        rows = query('SELECT * FROM "events"', db_path=":memory:")
        assert len(rows) == 3

    @patch("sandboxes.data.events_db.tushare_client")
    def test_partial_failure(self, mock_tc):
        """部分数据源返回 error 时，其他源照常处理。"""
        mock_tc.get_forecast.return_value = {"status": "error", "message": "timeout"}
        mock_tc.get_share_float.return_value = {
            "status": "ok",
            "data": [
                {"ts_code": "000988.SZ", "float_date": "20260501", "float_share": 500000.0, "ann_date": "20260401"},
            ],
        }
        mock_tc.get_stk_holdertrade.return_value = {"status": "error", "message": "no permission"}

        events = classify_events("000988.SZ", "20260101", "20260501", db_path=":memory:")

        assert len(events) == 1
        assert events[0]["event_type"] == EventType.IPO_UNLOCK.value

    @patch("sandboxes.data.events_db.tushare_client")
    def test_all_empty(self, mock_tc):
        """三个数据源都无数据时返回空列表。"""
        mock_tc.get_forecast.return_value = {"status": "ok", "data": []}
        mock_tc.get_share_float.return_value = {"status": "ok", "data": []}
        mock_tc.get_stk_holdertrade.return_value = {"status": "ok", "data": []}

        events = classify_events("000988.SZ", "20260101", "20260501", db_path=":memory:")
        assert len(events) == 0
