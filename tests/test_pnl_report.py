"""tests for tools/pnl_report.py"""
from unittest.mock import patch
import pytest

with patch("tools.pnl_report.tushare_client"):
    from tools.pnl_report import compute_pnl, compare_benchmark, generate_pnl_report


def test_compute_pnl_basic():
    history = [
        {"date": "20250101", "total_value": 1_000_000, "daily_return_pct": 0},
        {"date": "20250102", "total_value": 1_010_000, "daily_return_pct": 1.0},
        {"date": "20250103", "total_value": 1_005_000, "daily_return_pct": -0.5},
        {"date": "20250104", "total_value": 1_020_000, "daily_return_pct": 1.5},
        {"date": "20250105", "total_value": 1_030_000, "daily_return_pct": 0.98},
    ]
    result = compute_pnl(history)
    assert result["trading_days"] == 5
    assert result["cumulative_return_pct"] == pytest.approx(3.0, abs=0.1)
    assert result["max_drawdown_pct"] >= 0
    assert 0 <= result["win_rate"] <= 1
    assert result["sharpe"] != 0


def test_compute_pnl_empty():
    result = compute_pnl([])
    assert result == {"cumulative_return_pct": 0, "max_drawdown_pct": 0, "sharpe": 0, "win_rate": 0, "trading_days": 0}


def test_compare_benchmark():
    history = [
        {"date": "20250101", "total_value": 1_000_000, "daily_return_pct": 0},
        {"date": "20250102", "total_value": 1_050_000, "daily_return_pct": 5.0},
    ]
    benchmark = [
        {"trade_date": "20250101", "close": 4000},
        {"trade_date": "20250102", "close": 4080},
    ]
    result = compare_benchmark(history, benchmark)
    assert result["cumulative_return_pct"] == pytest.approx(5.0, abs=0.1)
    assert result["benchmark_return_pct"] == pytest.approx(2.0, abs=0.1)
    assert result["excess_return_pct"] == pytest.approx(3.0, abs=0.1)


def test_generate_report():
    history = [
        {"date": "20250101", "total_value": 1_000_000, "daily_return_pct": 0},
        {"date": "20250102", "total_value": 1_050_000, "daily_return_pct": 5.0},
    ]
    report = generate_pnl_report(history)
    assert "# 模拟盘 PnL 报告" in report
    assert "累计收益" in report
    assert "最大回撤" in report
    assert "夏普比率" in report
    assert "胜率" in report
