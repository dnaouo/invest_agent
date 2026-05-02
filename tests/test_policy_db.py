"""Tests for sandboxes.data.policy_db."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from sandboxes.data import duckdb_store
from sandboxes.data.policy_db import (
    get_themes_for_ptype,
    refresh_policy,
    search_policy,
)

_FAKE_RECORDS = [
    {
        "title": "关于促进半导体产业发展的若干意见",
        "pub_date": "20240315",
        "org": "国务院",
        "ptype": "科技",
        "content": "加快半导体自主可控",
    },
    {
        "title": "新能源汽车产业发展规划",
        "pub_date": "20240310",
        "org": "工信部",
        "ptype": "能源",
        "content": "推动新能源汽车普及",
    },
    {
        "title": "关于加强金融监管的通知",
        "pub_date": "20240301",
        "org": "央行",
        "ptype": "金融",
        "content": "防范系统性金融风险",
    },
]

DB_PATH = ":memory:"


@pytest.fixture(autouse=True)
def _clean_connections():
    """每个测试用例后清理 DuckDB 连接。"""
    yield
    duckdb_store._connections.clear()


def _mock_get_npr(**kwargs) -> dict:
    """根据参数过滤 _FAKE_RECORDS 返回。"""
    records = list(_FAKE_RECORDS)
    if kwargs.get("ptype"):
        records = [r for r in records if r["ptype"] == kwargs["ptype"]]
    if kwargs.get("org"):
        records = [r for r in records if r["org"] == kwargs["org"]]
    return {"status": "ok", "data": records}


class TestRefreshPolicy:
    @patch("sandboxes.data.policy_db.tushare_client.get_npr", side_effect=_mock_get_npr)
    def test_refresh_policy(self, mock_npr):
        count = refresh_policy(db_path=DB_PATH)
        assert count == len(_FAKE_RECORDS)
        mock_npr.assert_called_once()

    @patch("sandboxes.data.policy_db.tushare_client.get_npr", return_value={"status": "error", "message": "fail"})
    def test_refresh_policy_api_error(self, mock_npr):
        count = refresh_policy(db_path=DB_PATH)
        assert count == 0

    @patch("sandboxes.data.policy_db.tushare_client.get_npr", return_value={"status": "ok", "data": []})
    def test_refresh_policy_empty(self, mock_npr):
        count = refresh_policy(db_path=DB_PATH)
        assert count == 0


class TestSearchPolicy:
    @patch("sandboxes.data.policy_db.tushare_client.get_npr", side_effect=_mock_get_npr)
    def test_search_policy(self, mock_npr):
        refresh_policy(db_path=DB_PATH)
        results = search_policy(keyword="半导体", db_path=DB_PATH)
        assert len(results) == 1
        assert "半导体" in results[0]["title"]

    @patch("sandboxes.data.policy_db.tushare_client.get_npr", side_effect=_mock_get_npr)
    def test_search_policy_by_ptype(self, mock_npr):
        refresh_policy(db_path=DB_PATH)
        results = search_policy(ptype="金融", db_path=DB_PATH)
        assert len(results) == 1
        assert results[0]["ptype"] == "金融"

    @patch("sandboxes.data.policy_db.tushare_client.get_npr", side_effect=_mock_get_npr)
    def test_search_policy_empty(self, mock_npr):
        refresh_policy(db_path=DB_PATH)
        results = search_policy(keyword="不存在的政策", db_path=DB_PATH)
        assert results == []


class TestGetThemesForPtype:
    def test_known_ptype(self):
        themes = get_themes_for_ptype("科技")
        assert themes == ["半导体", "AI", "信创", "量子计算"]

    def test_unknown_ptype(self):
        themes = get_themes_for_ptype("未知类型")
        assert themes == []

    def test_all_ptypes(self):
        from sandboxes.data.policy_db import PTYPE_THEME_MAP
        for ptype, expected in PTYPE_THEME_MAP.items():
            assert get_themes_for_ptype(ptype) == expected
