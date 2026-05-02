"""Tests for sandboxes.data.router."""

from unittest.mock import patch

from sandboxes.data import router


@patch("sandboxes.data.tushare_client.get_daily")
def test_execute_tushare_route(mock_get_daily):
    mock_get_daily.return_value = {"status": "ok", "data": [{"close": 11.0}]}

    result = router.execute("data", "get_daily", {
        "ts_code": "000001.SZ",
        "start_date": "20260101",
        "end_date": "20260502",
    })

    assert result["status"] == "ok"
    assert result["data"] == [{"close": 11.0}]
    mock_get_daily.assert_called_once_with(
        ts_code="000001.SZ", start_date="20260101", end_date="20260502"
    )


@patch("sandboxes.data.akshare_client.get_cls_news")
def test_execute_akshare_route(mock_get_cls_news):
    mock_get_cls_news.return_value = {"status": "ok", "data": [{"title": "test"}]}

    result = router.execute("data", "get_cls_news", {"count": 10})

    assert result["status"] == "ok"
    assert result["data"] == [{"title": "test"}]
    mock_get_cls_news.assert_called_once_with(count=10)


def test_execute_unknown_api():
    result = router.execute("data", "nonexistent_api", {})

    assert result["status"] == "error"
    assert result["error_code"] == "UNKNOWN_API"
    assert "nonexistent_api" in result["message"]


def test_execute_unknown_source():
    result = router.execute("wrong_source", "get_daily", {})

    assert result["status"] == "error"
    assert result["error_code"] == "UNKNOWN_SOURCE"
