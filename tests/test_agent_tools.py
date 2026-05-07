"""Tests for tools/agent_tools.py — 7 个 tool 各 1 个 mock 测试。"""
from unittest.mock import patch, MagicMock
import pytest

from sandboxes.data import duckdb_store
from sandboxes.data.duckdb_store import upsert, query


@pytest.fixture(autouse=True)
def _clean_duckdb():
    yield
    duckdb_store._connections.clear()


def _setup_table(table_name, records, keys, db_path=":memory:"):
    """向 :memory: 数据库写入测试数据。"""
    upsert(table_name, records, keys, db_path=db_path)


class TestSearchReports:
    def test_found(self):
        _setup_table("research_report", [
            {"title": "光模块行业深度", "inst_csname": "中信证券", "report_type": "行业", "report_date": "20260505", "abstr": "看好光模块"},
        ], ["title", "report_date"])
        from tools.agent_tools import search_reports
        result = search_reports("光模块", db_path=":memory:")
        assert "光模块" in result
        assert "中信证券" in result


class TestSearchPolicy:
    def test_found(self):
        _setup_table("policy", [
            {"title": "半导体产业支持政策", "org": "工信部", "pub_date": "20260501"},
        ], ["title", "pub_date"])
        from tools.agent_tools import search_policy
        result = search_policy("半导体", db_path=":memory:")
        assert "半导体" in result
        assert "工信部" in result


class TestMatchHotMoney:
    def test_match(self):
        _setup_table("top_list", [
            {"ts_code": "000001.SZ", "trade_date": "20260506", "exalter": "华泰深圳", "buy": 5000, "sell": 100},
        ], ["ts_code", "trade_date", "exalter"])
        _setup_table("hm_list", [
            {"hm_name": "赵老哥", "broker": "华泰深圳"},
        ], ["hm_name"])
        from tools.agent_tools import match_hot_money
        result = match_hot_money("20260506", db_path=":memory:")
        assert "赵老哥" in result
        assert "买入" in result


@patch("tools.agent_tools.akshare_client")
class TestGetNorthIndividual:
    def test_ok(self, mock_ak):
        mock_ak.get_north_flow_individual.return_value = {
            "status": "ok",
            "data": [
                {"date": "20260505", "shareholding": 100000, "close_amt": 500},
                {"date": "20260504", "shareholding": 99000, "close_amt": 490},
            ],
        }
        from tools.agent_tools import get_north_individual
        result = get_north_individual("000988.SZ")
        assert "持股" in result
        assert "20260505" in result


class TestSearchNews:
    def test_found(self):
        _setup_table("news", [
            {"title": "央行降息", "time": "10:30", "source": "cls"},
            {"title": "美股大涨", "time": "11:00", "source": "jin10"},
        ], ["source"])
        from tools.agent_tools import search_news
        result = search_news("央行", db_path=":memory:")
        assert "央行" in result


@patch("tools.agent_tools.tushare_client")
class TestGetThemeMembers:
    def test_ok(self, mock_ts):
        mock_ts.get_ths_index.return_value = {
            "status": "ok",
            "data": [{"ts_code": "THS001", "name": "CPO概念"}],
        }
        mock_ts.get_ths_member.return_value = {
            "status": "ok",
            "data": [{"code": "002475", "name": "立讯精密"}],
        }
        from tools.agent_tools import get_theme_members
        result = get_theme_members("CPO")
        assert "CPO" in result
        assert "立讯精密" in result


@patch("tools.agent_tools.classify_events.__module__", "tools.agent_tools")
class TestClassifyEvents:
    @patch("sandboxes.data.events_db.classify_events")
    def test_ok(self, mock_classify):
        mock_classify.return_value = [
            {"ann_date": "20260501", "event_type": "业绩预告", "strength": 0.8, "detail": "净利润同比+50%"},
        ]
        from tools.agent_tools import classify_events
        result = classify_events("000001.SZ", days=30)
        assert "业绩预告" in result
