"""Tests for seats_db + seats_join — all mocked, DuckDB :memory:."""

from unittest.mock import patch

import pytest

from sandboxes.data.duckdb_store import _connections
from sandboxes.data.seats_db import refresh_seats, lookup_seat
from sandboxes.data.seats_join import get_today_hot_money


DB = ":memory:"

FAKE_HM_LIST = [
    {"hm_name": "赵老哥", "hm_code": "ZLG", "broker": "华鑫证券上海宛平南路", "style": "打板"},
    {"hm_name": "炒股养家", "hm_code": "CGYJ", "broker": "国信证券深圳泰然九路", "style": "低吸"},
    {"hm_name": "小鳄鱼", "hm_code": "XEY", "broker": "华泰证券深圳益田路荣超商务中心", "style": "趋势"},
]


@pytest.fixture(autouse=True)
def _clean_db():
    """每个测试后清理 :memory: 连接缓存。"""
    yield
    conn = _connections.pop(DB, None)
    if conn is not None:
        conn.close()


# ── refresh_seats ─────────────────────────────────────────────

@patch("sandboxes.data.seats_db.tushare_client.get_hm_list")
def test_refresh_seats(mock_hm):
    mock_hm.return_value = {"status": "ok", "data": FAKE_HM_LIST}
    count = refresh_seats(db_path=DB)
    assert count == 3

    from sandboxes.data.duckdb_store import query
    rows = query("SELECT * FROM hm_list", db_path=DB)
    assert len(rows) == 3
    names = {r["hm_name"] for r in rows}
    assert "赵老哥" in names


# ── lookup_seat ───────────────────────────────────────────────

@patch("sandboxes.data.seats_db.tushare_client.get_hm_list")
def test_lookup_seat_found(mock_hm):
    mock_hm.return_value = {"status": "ok", "data": FAKE_HM_LIST}
    refresh_seats(db_path=DB)

    hit = lookup_seat("赵老哥", db_path=DB)
    assert hit is not None
    assert hit["hm_name"] == "赵老哥"
    assert hit["style"] == "打板"


@patch("sandboxes.data.seats_db.tushare_client.get_hm_list")
def test_lookup_seat_not_found(mock_hm):
    mock_hm.return_value = {"status": "ok", "data": FAKE_HM_LIST}
    refresh_seats(db_path=DB)

    hit = lookup_seat("不存在的营业部", db_path=DB)
    assert hit is None


# ── get_today_hot_money ───────────────────────────────────────

@patch("sandboxes.data.seats_join.tushare_client.get_block_trade")
@patch("sandboxes.data.seats_join.tushare_client.get_top_list")
@patch("sandboxes.data.seats_db.tushare_client.get_hm_list")
def test_get_today_hot_money(mock_hm, mock_top, mock_block):
    mock_hm.return_value = {"status": "ok", "data": FAKE_HM_LIST}
    refresh_seats(db_path=DB)

    mock_top.return_value = {
        "status": "ok",
        "data": [
            {
                "ts_code": "000001.SZ",
                "trade_date": "20260502",
                "exalter": "赵老哥",
                "buy": 50000000.0,
                "sell": 0.0,
                "net_buy": 50000000.0,
            },
            {
                "ts_code": "600000.SH",
                "trade_date": "20260502",
                "exalter": "路人甲营业部",
                "buy": 10000000.0,
                "sell": 5000000.0,
                "net_buy": 5000000.0,
            },
        ],
    }
    mock_block.return_value = {
        "status": "ok",
        "data": [
            {
                "ts_code": "000002.SZ",
                "trade_date": "20260502",
                "buyer": "炒股养家",
                "seller": "某机构",
                "price": 15.0,
                "vol": 1000000,
                "amount": 15000000.0,
            },
        ],
    }

    results = get_today_hot_money("20260502", db_path=DB)

    top_matches = [r for r in results if r["source"] == "top_list"]
    assert len(top_matches) == 1
    assert top_matches[0]["broker"] == "赵老哥"
    assert top_matches[0]["ts_code"] == "000001.SZ"

    block_matches = [r for r in results if r["source"] == "block_trade"]
    assert len(block_matches) == 1
    assert block_matches[0]["broker"] == "炒股养家"
    assert block_matches[0]["side"] == "buyer"
