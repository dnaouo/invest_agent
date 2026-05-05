"""Tests for sandboxes.backtest.runner."""
from unittest.mock import patch

from sandboxes.backtest.runner import run_simple_backtest, BacktestResult


def _daily_data(prices: list[float]) -> dict:
    records = [{"trade_date": f"2026010{i+1}", "close": p} for i, p in enumerate(prices)]
    return {"status": "ok", "data": records}


@patch("sandboxes.backtest.runner.tushare_client")
def test_simple_backtest_success(mock_ts):
    mock_ts.get_daily.return_value = _daily_data([10, 10.5, 11, 10.8, 11.2])
    result = run_simple_backtest("000988.SZ", "20260101", "20260105")
    assert isinstance(result, BacktestResult)
    assert result.total_return_pct > 0
    assert result.max_drawdown >= 0
    assert 0 <= result.win_rate <= 1


@patch("sandboxes.backtest.runner.tushare_client")
def test_simple_backtest_no_data(mock_ts):
    mock_ts.get_daily.return_value = {"status": "error", "message": "no data"}
    result = run_simple_backtest("000988.SZ", "20260101", "20260105")
    assert result.sharpe == 0.0
    assert result.total_return_pct == 0.0


@patch("sandboxes.backtest.runner.tushare_client")
def test_simple_backtest_sell(mock_ts):
    mock_ts.get_daily.return_value = _daily_data([11, 10.5, 10, 9.5, 9])
    result = run_simple_backtest("000988.SZ", "20260101", "20260105", signal_direction="sell")
    assert result.total_return_pct > 0
