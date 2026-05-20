"""signal_discovery.py 单元测试。"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from sandboxes.data import duckdb_store
from sandboxes.data.duckdb_store import upsert


@pytest.fixture(autouse=True)
def _clean_duckdb():
    """每个测试用例独立的 :memory: 连接。"""
    yield
    duckdb_store._connections.pop(":memory:", None)


def _setup_table(table_name: str, records: list[dict], keys: list[str]):
    """在 :memory: 中创建测试表并写入数据。"""
    upsert(table_name, records, keys, db_path=":memory:")


class TestScanResearchUpgrades:
    def test_broker_count_triggers(self):
        from harness.signal_discovery import _scan_research_upgrades

        _setup_table("research_report", [
            {"ts_code": "002428.SZ", "name": "云南锗业", "inst_csname": "中信证券", "title": "深度报告", "trade_date": "20260401", "abstr": "", "report_type": "深度"},
            {"ts_code": "002428.SZ", "name": "云南锗业", "inst_csname": "国泰君安", "title": "调研报告", "trade_date": "20260401", "abstr": "", "report_type": "深度"},
            {"ts_code": "002428.SZ", "name": "云南锗业", "inst_csname": "海通证券", "title": "行业报告", "trade_date": "20260402", "abstr": "", "report_type": "深度"},
        ], ["title", "trade_date"])

        result = _scan_research_upgrades("20260402", ":memory:")
        assert len(result) >= 1
        assert result[0]["ts_code"] == "002428.SZ"
        assert result[0]["trigger_source"] == "research_upgrade"

    def test_rating_keywords_trigger(self):
        from harness.signal_discovery import _scan_research_upgrades

        _setup_table("research_report", [
            {"ts_code": "600519.SH", "name": "贵州茅台", "inst_csname": "A", "title": "首次覆盖-买入", "trade_date": "20260401", "abstr": "", "report_type": ""},
            {"ts_code": "600519.SH", "name": "贵州茅台", "inst_csname": "B", "title": "维持买入评级", "trade_date": "20260401", "abstr": "", "report_type": ""},
            {"ts_code": "600519.SH", "name": "贵州茅台", "inst_csname": "C", "title": "上调至增持", "trade_date": "20260402", "abstr": "", "report_type": ""},
        ], ["title", "trade_date"])

        result = _scan_research_upgrades("20260402", ":memory:")
        codes = [s["ts_code"] for s in result]
        assert "600519.SH" in codes

    def test_no_triggers_below_threshold(self):
        from harness.signal_discovery import _scan_research_upgrades

        _setup_table("research_report", [
            {"ts_code": "000001.SZ", "name": "平安银行", "inst_csname": "A", "title": "报告", "trade_date": "20260401", "abstr": "", "report_type": ""},
            {"ts_code": "000001.SZ", "name": "平安银行", "inst_csname": "B", "title": "报告2", "trade_date": "20260401", "abstr": "", "report_type": ""},
        ], ["title", "trade_date"])

        result = _scan_research_upgrades("20260402", ":memory:")
        codes = [s["ts_code"] for s in result]
        assert "000001.SZ" not in codes


class TestScanSectorAnomaly:
    @patch("harness.signal_discovery.tushare_client")
    def test_single_day_large_inflow(self, mock_ts):
        from harness.signal_discovery import _scan_sector_anomaly

        _setup_table("moneyflow_cnt_ths", [
            {"ts_code": "885600.TI", "name": "光模块", "net_amount": "200000000", "trade_date": "20260402"},
        ], ["ts_code", "trade_date"])

        mock_ts.get_ths_member.return_value = {
            "status": "ok",
            "data": [
                {"code": "002281.SZ", "name": "光迅科技"},
                {"code": "300308.SZ", "name": "中际旭创"},
            ],
        }

        result = _scan_sector_anomaly("20260402", ":memory:")
        assert len(result) >= 1
        codes = [s["ts_code"] for s in result]
        assert "002281.SZ" in codes

    @patch("harness.signal_discovery.tushare_client")
    def test_api_failure_graceful(self, mock_ts):
        from harness.signal_discovery import _scan_sector_anomaly

        _setup_table("moneyflow_cnt_ths", [
            {"ts_code": "885600.TI", "name": "光模块", "net_amount": "200000000", "trade_date": "20260402"},
        ], ["ts_code", "trade_date"])

        mock_ts.get_ths_member.side_effect = Exception("API限流")

        result = _scan_sector_anomaly("20260402", ":memory:")
        assert len(result) >= 1
        assert "未获取成分股" in result[0]["trigger_detail"]


class TestScanNewsCluster:
    def test_keyword_frequency_trigger(self):
        from harness.signal_discovery import _scan_news_cluster

        news = [{"title": f"光模块需求大增第{i}波", "time": "20260401", "source": "cls"} for i in range(6)]
        _setup_table("news", news, ["title", "source"])

        result = _scan_news_cluster("20260402", ":memory:")
        assert len(result) >= 1
        assert "光模块" in result[0]["trigger_detail"]

    def test_below_threshold_no_trigger(self):
        from harness.signal_discovery import _scan_news_cluster

        news = [{"title": f"光模块新闻{i}", "time": "20260401", "source": "cls"} for i in range(3)]
        _setup_table("news", news, ["title", "source"])

        result = _scan_news_cluster("20260402", ":memory:")
        triggered_kws = [s for s in result if "光模块" in s.get("trigger_detail", "")]
        assert len(triggered_kws) == 0


class TestScanEarningsBeat:
    @patch("harness.signal_discovery.tushare_client")
    def test_forecast_preincrement(self, mock_ts):
        from harness.signal_discovery import _scan_earnings_beat

        mock_ts.get_forecast_vip.return_value = {
            "status": "ok",
            "data": [
                {"ts_code": "002428.SZ", "name": "云南锗业", "type": "预增", "change_min": "50"},
                {"ts_code": "000001.SZ", "name": "平安银行", "type": "预减", "change_min": "-20"},
                {"ts_code": "600519.SH", "name": "贵州茅台", "type": "预增", "change_min": "10"},
            ],
        }

        result = _scan_earnings_beat("20260402", ":memory:")
        assert len(result) == 1
        assert result[0]["ts_code"] == "002428.SZ"
        assert "50%" in result[0]["trigger_detail"]

    @patch("harness.signal_discovery.tushare_client")
    def test_api_error_returns_empty(self, mock_ts):
        from harness.signal_discovery import _scan_earnings_beat

        mock_ts.get_forecast_vip.side_effect = Exception("连接超时")

        result = _scan_earnings_beat("20260402", ":memory:")
        assert result == []


class TestScanHotMoney:
    def test_known_seat_large_buy(self):
        from harness.signal_discovery import _scan_hot_money

        _setup_table("top_inst", [
            {"ts_code": "002428.SZ", "exalter": "东方财富拉萨", "buy": "80000000", "sell": "10000000", "trade_date": "20260402"},
        ], ["ts_code", "trade_date"])
        _setup_table("hm_list", [
            {"name": "赵老哥", "orgs": "东方财富拉萨,华鑫证券上海", "desc": ""},
        ], ["name"])

        result = _scan_hot_money("20260402", ":memory:")
        assert len(result) >= 1
        assert result[0]["ts_code"] == "002428.SZ"
        assert "赵老哥" in result[0]["trigger_detail"]

    def test_below_threshold_no_trigger(self):
        from harness.signal_discovery import _scan_hot_money

        _setup_table("top_inst", [
            {"ts_code": "002428.SZ", "exalter": "东方财富拉萨", "buy": "30000000", "sell": "10000000", "trade_date": "20260402"},
        ], ["ts_code", "trade_date"])
        _setup_table("hm_list", [
            {"name": "赵老哥", "orgs": "东方财富拉萨", "desc": ""},
        ], ["name"])

        result = _scan_hot_money("20260402", ":memory:")
        assert len(result) == 0


class TestGetMarketPulse:
    def test_high_limit_up_is_climax(self):
        from harness.signal_discovery import _get_market_pulse

        records = [{"ts_code": f"00000{i}.SZ", "trade_date": "20260402", "limit": "U"} for i in range(70)]
        records += [{"ts_code": f"60000{i}.SH", "trade_date": "20260402", "limit": "D"} for i in range(10)]
        _setup_table("limit_list", records, ["ts_code", "trade_date"])

        result = _get_market_pulse("20260402", ":memory:")
        assert result["limit_up_count"] == 70
        assert result["limit_down_count"] == 10
        assert result["phase"] == "高潮"

    def test_fermentation_phase(self):
        from harness.signal_discovery import _get_market_pulse

        records = [{"ts_code": f"00{i:04d}.SZ", "trade_date": "20260402", "limit": "U"} for i in range(45)]
        records += [{"ts_code": f"60{i:04d}.SH", "trade_date": "20260402", "limit": "D"} for i in range(12)]
        _setup_table("limit_list", records, ["ts_code", "trade_date"])

        result = _get_market_pulse("20260402", ":memory:")
        assert result["phase"] == "发酵"

    def test_freeze_phase(self):
        from harness.signal_discovery import _get_market_pulse

        records = [{"ts_code": f"00{i:04d}.SZ", "trade_date": "20260402", "limit": "U"} for i in range(10)]
        records += [{"ts_code": f"60{i:04d}.SH", "trade_date": "20260402", "limit": "D"} for i in range(5)]
        _setup_table("limit_list", records, ["ts_code", "trade_date"])

        result = _get_market_pulse("20260402", ":memory:")
        assert result["phase"] == "冰点"

    def test_retreat_phase(self):
        from harness.signal_discovery import _get_market_pulse

        records = [{"ts_code": f"00{i:04d}.SZ", "trade_date": "20260402", "limit": "U"} for i in range(20)]
        records += [{"ts_code": f"60{i:04d}.SH", "trade_date": "20260402", "limit": "D"} for i in range(35)]
        _setup_table("limit_list", records, ["ts_code", "trade_date"])

        result = _get_market_pulse("20260402", ":memory:")
        assert result["phase"] == "退潮"


class TestMergeSignals:
    def test_same_code_merges(self):
        from harness.signal_discovery import _merge_signals

        signals = [
            {"ts_code": "002428.SZ", "stock_name": "云南锗业", "trigger_source": "research_upgrade", "trigger_detail": "3家覆盖", "priority": "medium"},
            {"ts_code": "002428.SZ", "stock_name": "云南锗业", "trigger_source": "hot_money", "trigger_detail": "游资买入", "priority": "high"},
        ]
        result = _merge_signals(signals)
        assert len(result) == 1
        assert result[0]["priority"] == "high"
        assert "3家覆盖" in result[0]["trigger_detail"]
        assert "游资买入" in result[0]["trigger_detail"]

    def test_different_codes_not_merged(self):
        from harness.signal_discovery import _merge_signals

        signals = [
            {"ts_code": "002428.SZ", "stock_name": "云南锗业", "trigger_source": "research_upgrade", "trigger_detail": "detail1", "priority": "high"},
            {"ts_code": "600519.SH", "stock_name": "贵州茅台", "trigger_source": "hot_money", "trigger_detail": "detail2", "priority": "medium"},
        ]
        result = _merge_signals(signals)
        assert len(result) == 2

    def test_sorted_by_priority(self):
        from harness.signal_discovery import _merge_signals

        signals = [
            {"ts_code": "000001.SZ", "stock_name": "A", "trigger_source": "x", "trigger_detail": "d1", "priority": "low"},
            {"ts_code": "000002.SZ", "stock_name": "B", "trigger_source": "y", "trigger_detail": "d2", "priority": "high"},
            {"ts_code": "000003.SZ", "stock_name": "C", "trigger_source": "z", "trigger_detail": "d3", "priority": "medium"},
        ]
        result = _merge_signals(signals)
        assert result[0]["priority"] == "high"
        assert result[1]["priority"] == "medium"
        assert result[2]["priority"] == "low"

    def test_empty_ts_code_not_merged(self):
        from harness.signal_discovery import _merge_signals

        signals = [
            {"ts_code": "", "stock_name": "", "trigger_source": "news_cluster", "trigger_detail": "kw1", "priority": "medium"},
            {"ts_code": "", "stock_name": "", "trigger_source": "news_cluster", "trigger_detail": "kw2", "priority": "high"},
        ]
        result = _merge_signals(signals)
        assert len(result) == 2


class TestScanMajorAnnouncements:
    def test_empty_when_no_announcements(self):
        from harness.signal_discovery import _scan_major_announcements

        result = _scan_major_announcements("20260402", ":memory:")
        assert result == []

    def test_keyword_match(self):
        from harness.signal_discovery import _scan_major_announcements

        _setup_table("announcements", [
            {"ts_code": "002428.SZ", "title": "关于扩产100MW光伏项目的公告", "category": "一般公告", "ann_date": "20260402"},
            {"ts_code": "600519.SH", "title": "关于日常经营的公告", "category": "一般公告", "ann_date": "20260402"},
        ], ["ts_code", "ann_date"])

        result = _scan_major_announcements("20260402", ":memory:")
        assert len(result) == 1
        assert result[0]["ts_code"] == "002428.SZ"
        assert "扩产" in result[0]["trigger_detail"]
        assert result[0]["trigger_source"] == "major_announcement"

    def test_category_match(self):
        from harness.signal_discovery import _scan_major_announcements

        _setup_table("announcements", [
            {"ts_code": "000988.SZ", "title": "关于重大资产购买进展的公告", "category": "重大事项", "ann_date": "20260402"},
        ], ["ts_code", "ann_date"])

        result = _scan_major_announcements("20260402", ":memory:")
        assert len(result) == 1
        assert result[0]["ts_code"] == "000988.SZ"
        assert "重大事项" in result[0]["trigger_detail"]
        assert result[0]["priority"] == "high"

    def test_ts_code_normalize_6digit(self):
        from harness.signal_discovery import _scan_major_announcements

        _setup_table("announcements", [
            {"ts_code": "002428", "title": "关于收购子公司的公告", "category": "一般公告", "ann_date": "20260402"},
            {"ts_code": "600519", "title": "关于定增方案的公告", "category": "融资公告", "ann_date": "20260402"},
            {"ts_code": "300308", "title": "关于投资设立合资公司的公告", "category": "一般公告", "ann_date": "20260402"},
        ], ["ts_code", "ann_date"])

        result = _scan_major_announcements("20260402", ":memory:")
        codes = [s["ts_code"] for s in result]
        assert "002428.SZ" in codes
        assert "600519.SH" in codes
        assert "300308.SZ" in codes

    def test_same_stock_multiple_announcements_merged(self):
        from harness.signal_discovery import _scan_major_announcements

        _setup_table("announcements", [
            {"ts_code": "002428.SZ", "title": "关于扩产100MW项目的公告", "category": "一般公告", "ann_date": "20260402"},
            {"ts_code": "002428.SZ", "title": "关于收购子公司股权的公告", "category": "重大事项", "ann_date": "20260402"},
        ], ["ts_code", "ann_date"])

        result = _scan_major_announcements("20260402", ":memory:")
        assert len(result) == 1
        assert result[0]["ts_code"] == "002428.SZ"
        assert "扩产" in result[0]["trigger_detail"]
        assert "重大事项" in result[0]["trigger_detail"]


class TestDiscoverSignals:
    @patch("harness.signal_discovery.tushare_client")
    def test_full_pipeline(self, mock_ts):
        from harness.signal_discovery import discover_signals

        _setup_table("research_report", [
            {"ts_code": "002428.SZ", "name": "云南锗业", "inst_csname": f"券商{i}", "title": "报告", "trade_date": "20260401", "abstr": "", "report_type": ""}
            for i in range(4)
        ], ["title", "trade_date"])
        _setup_table("limit_list", [
            {"ts_code": f"00{i:04d}.SZ", "trade_date": "20260402", "limit": "U"} for i in range(45)
        ] + [
            {"ts_code": f"60{i:04d}.SH", "trade_date": "20260402", "limit": "D"} for i in range(10)
        ], ["ts_code", "trade_date"])

        mock_ts.get_forecast_vip.return_value = {"status": "ok", "data": []}
        mock_ts.get_ths_member.return_value = {"status": "ok", "data": []}

        result = discover_signals("20260402", db_path=":memory:")

        assert result["trade_date"] == "20260402"
        assert isinstance(result["signals"], list)
        assert result["market_pulse"]["phase"] == "发酵"
        codes = [s["ts_code"] for s in result["signals"]]
        assert "002428.SZ" in codes
