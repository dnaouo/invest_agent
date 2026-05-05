"""tests for tools.time_slice — 防 look-ahead 信息切片。"""
from tools.time_slice import slice_data, slice_financial


class TestSliceDataBasic:
    def test_slice_data_basic(self):
        data = [
            {"trade_date": "20250501", "close": 10.0},
            {"trade_date": "20250502", "close": 11.0},
            {"trade_date": "20250503", "close": 12.0},
        ]
        result = slice_data(data, "20250502")
        assert len(result) == 2
        assert result[0]["trade_date"] == "20250501"
        assert result[1]["trade_date"] == "20250502"

    def test_slice_data_empty(self):
        assert slice_data([], "20250502") == []

    def test_slice_data_missing_field(self):
        data = [
            {"trade_date": "20250501", "close": 10.0},
            {"close": 11.0},  # 缺少 trade_date
            {"trade_date": None, "close": 12.0},
        ]
        result = slice_data(data, "20250510")
        assert len(result) == 1
        assert result[0]["trade_date"] == "20250501"


class TestSliceFinancial:
    def test_slice_financial(self):
        data = [
            {"ann_date": "20250401", "end_date": "20241231", "revenue": 100},
            {"ann_date": "20250420", "end_date": "20250331", "revenue": 120},
            {"ann_date": "20250715", "end_date": "20250630", "revenue": 130},
        ]
        result = slice_financial(data, "20250501")
        assert len(result) == 2
        dates = [r["ann_date"] for r in result]
        assert "20250715" not in dates
        assert "20250401" in dates
        assert "20250420" in dates


class TestNoFutureLeakage:
    def test_no_future_leakage(self):
        data = [{"trade_date": f"202505{i:02d}", "val": i} for i in range(1, 21)]
        result = slice_data(data, "20250510")
        assert len(result) == 10
        for r in result:
            assert r["trade_date"] <= "20250510"
