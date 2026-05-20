from unittest.mock import patch
import pandas as pd
from tools import symbol_resolver


@patch("tools.symbol_resolver._fetch_stock_basic")
def test_validate_matches(mock_fetch):
    mock_fetch.return_value = pd.DataFrame([
        {"ts_code": "600396.SH", "name": "华电辽能"},
        {"ts_code": "000609.SZ", "name": "*ST 中迪"},
    ])
    r = symbol_resolver.validate("600396.SH", "华电辽能")
    assert r["valid"] is True
    assert r["actual_name"] == "华电辽能"


@patch("tools.symbol_resolver._fetch_stock_basic")
def test_validate_mismatch_returns_suggestions(mock_fetch):
    mock_fetch.return_value = pd.DataFrame([
        {"ts_code": "600396.SH", "name": "华电辽能"},
        {"ts_code": "000609.SZ", "name": "*ST 中迪"},
    ])
    r = symbol_resolver.validate("000609.SZ", "华电辽能")
    assert r["valid"] is False
    assert r["actual_name"] == "*ST 中迪"
    assert any("600396" in s for s in r["suggestions"])


@patch("tools.symbol_resolver._fetch_stock_basic")
def test_resolve_by_name_fuzzy(mock_fetch):
    mock_fetch.return_value = pd.DataFrame([
        {"ts_code": "600396.SH", "name": "华电辽能"},
    ])
    matches = symbol_resolver.resolve_by_name("华电辽能")
    assert any(m["ts_code"] == "600396.SH" for m in matches)
