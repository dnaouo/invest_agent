"""研报库单元测试。使用 DuckDB :memory: 隔离。"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest

from sandboxes.data import tushare_client
from sandboxes.data.duckdb_store import _connections
from sandboxes.data.research_report_db import (
    detect_rating_change,
    get_recent_reports,
    refresh_reports,
)

_DB = ":memory:"

TODAY = datetime.now().strftime("%Y%m%d")


def _make_report(
    title: str,
    abstr: str = "",
    inst_csname: str = "测试证券",
    report_type: str = "深度报告",
    report_date: str = TODAY,
) -> dict:
    return {
        "title": title,
        "abstr": abstr,
        "author": "分析师A",
        "inst_csname": inst_csname,
        "report_type": report_type,
        "ind_name": "计算机",
        "url": "https://example.com/report",
        "report_date": report_date,
    }


@pytest.fixture(autouse=True)
def _clean_db():
    """每个测试前后清理内存连接。"""
    _connections.pop(_DB, None)
    yield
    conn = _connections.pop(_DB, None)
    if conn is not None:
        conn.close()


def test_refresh_reports():
    """mock tushare 返回几条研报，验证入库行数。"""
    fake_data = [
        _make_report("贵州茅台深度报告"),
        _make_report("宁德时代跟踪报告"),
        _make_report("比亚迪买入评级"),
    ]
    with patch.object(
        tushare_client,
        "get_research_report",
        return_value={"status": "ok", "data": fake_data},
    ):
        count = refresh_reports(TODAY, db_path=_DB)

    assert count == 3


def test_get_recent_reports():
    """refresh 后查询某只股票相关研报。"""
    fake_data = [
        _make_report("贵州茅台深度报告", abstr="茅台业绩超预期"),
        _make_report("宁德时代跟踪报告"),
        _make_report("贵州茅台估值分析"),
    ]
    with patch.object(
        tushare_client,
        "get_research_report",
        return_value={"status": "ok", "data": fake_data},
    ):
        refresh_reports(TODAY, db_path=_DB)

    reports = get_recent_reports("茅台", days=30, db_path=_DB)
    assert len(reports) == 2
    titles = {r["title"] for r in reports}
    assert "贵州茅台深度报告" in titles
    assert "贵州茅台估值分析" in titles


def test_detect_rating_change_signal():
    """mock 5 条不同券商的"买入"评级研报，验证 signal=True。"""
    fake_data = [
        _make_report("比亚迪买入评级", inst_csname="中信证券", report_type="买入"),
        _make_report("比亚迪投资价值分析", inst_csname="国泰君安", report_type="买入"),
        _make_report("比亚迪深度研究", inst_csname="华泰证券", report_type="上调"),
        _make_report("比亚迪行业领先", inst_csname="招商证券", report_type="买入"),
        _make_report("比亚迪新能源龙头", inst_csname="海通证券", report_type="买入"),
    ]
    with patch.object(
        tushare_client,
        "get_research_report",
        return_value={"status": "ok", "data": fake_data},
    ):
        refresh_reports(TODAY, db_path=_DB)

    result = detect_rating_change("比亚迪", days=30, db_path=_DB)
    assert result["signal"] is True
    assert result["count"] >= 3
    assert len(result["institutions"]) >= 3


def test_detect_rating_change_no_signal():
    """mock 1 条研报，验证 signal=False。"""
    fake_data = [
        _make_report("比亚迪跟踪报告", inst_csname="中信证券", report_type="买入"),
    ]
    with patch.object(
        tushare_client,
        "get_research_report",
        return_value={"status": "ok", "data": fake_data},
    ):
        refresh_reports(TODAY, db_path=_DB)

    result = detect_rating_change("比亚迪", days=30, db_path=_DB)
    assert result["signal"] is False
    assert result["count"] == 1
    assert result["institutions"] == ["中信证券"]
