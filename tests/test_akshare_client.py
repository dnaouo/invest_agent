"""Akshare 客户端单元测试。"""

from unittest.mock import patch

import pandas as pd

from sandboxes.data.akshare_client import get_cls_news, get_north_flow_individual


@patch("sandboxes.data.akshare_client.ak.stock_info_global_cls")
def test_get_cls_news_success(mock_cls):
    mock_cls.return_value = pd.DataFrame(
        {"title": ["新闻A", "新闻B"], "content": ["内容A", "内容B"]}
    )
    result = get_cls_news(count=2)
    assert result["status"] == "ok"
    assert isinstance(result["data"], list)
    assert len(result["data"]) == 2
    assert result["data"][0]["title"] == "新闻A"
    mock_cls.assert_called_once()


@patch("sandboxes.data.akshare_client.ak.stock_hsgt_individual_em")
def test_get_north_flow_individual_success(mock_hsgt):
    mock_hsgt.return_value = pd.DataFrame(
        {"date": ["2026-05-01"], "value": [123.45]}
    )
    result = get_north_flow_individual(symbol="000001")
    assert result["status"] == "ok"
    assert isinstance(result["data"], list)
    assert len(result["data"]) == 1
    assert result["data"][0]["value"] == 123.45
    mock_hsgt.assert_called_once_with(symbol="000001")
