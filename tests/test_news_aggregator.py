"""新闻聚合器单元测试。"""

from unittest.mock import patch

from sandboxes.data.news_aggregator import fetch_latest_news


_CLS_OK = {
    "status": "ok",
    "data": [
        {"标题": "CLS新闻A", "内容": "内容A", "发布日期": "2026-05-02", "发布时间": "10:00:00"},
        {"标题": "CLS新闻B", "内容": "内容B", "发布日期": "2026-05-02", "发布时间": "09:30:00"},
        {"标题": "重复标题", "内容": "CLS版本", "发布日期": "2026-05-02", "发布时间": "09:00:00"},
    ],
}

_JIN10_OK = {
    "status": "ok",
    "data": [
        {"时间": "2026-05-02 10:05:00", "内容": "JIN10新闻X"},
        {"时间": "2026-05-02 09:45:00", "内容": "JIN10新闻Y"},
        {"时间": "2026-05-02 09:00:00", "内容": "重复标题"},
    ],
}

_ERROR_RESP = {
    "status": "error",
    "error_code": "AKSHARE_API_ERROR",
    "message": "connection failed",
    "retry_hint": False,
}


@patch("sandboxes.data.news_aggregator.akshare_client.get_jin10_news")
@patch("sandboxes.data.news_aggregator.akshare_client.get_cls_news")
def test_fetch_latest_news(mock_cls, mock_jin10):
    mock_cls.return_value = _CLS_OK
    mock_jin10.return_value = _JIN10_OK

    result = fetch_latest_news(count=50, db_path=":memory:")

    assert isinstance(result, list)
    assert len(result) > 0

    sources = {r["source"] for r in result}
    assert "cls" in sources
    assert "jin10" in sources

    for r in result:
        assert "title" in r
        assert "content" in r
        assert "time" in r
        assert "source" in r

    titles = [r["title"] for r in result]
    assert titles.count("重复标题") == 1

    times = [r["time"] for r in result]
    assert times == sorted(times, reverse=True)


@patch("sandboxes.data.news_aggregator.akshare_client.get_jin10_news")
@patch("sandboxes.data.news_aggregator.akshare_client.get_cls_news")
def test_fetch_latest_news_one_source_fails(mock_cls, mock_jin10):
    mock_cls.return_value = _ERROR_RESP
    mock_jin10.return_value = _JIN10_OK

    result = fetch_latest_news(count=50, db_path=":memory:")

    assert isinstance(result, list)
    assert len(result) > 0
    assert all(r["source"] == "jin10" for r in result)

    mock_cls.return_value = _CLS_OK
    mock_jin10.return_value = _ERROR_RESP

    result = fetch_latest_news(count=50, db_path=":memory:")

    assert isinstance(result, list)
    assert len(result) > 0
    assert all(r["source"] == "cls" for r in result)
