"""tests for sandboxes.risk.engine — 风控规则引擎。"""
from sandboxes.risk.engine import (
    check_blacklist,
    check_portfolio_drawdown,
    check_position_limit,
    check_stop_loss,
)


class TestBlacklist:
    def test_blacklist_st(self):
        blocked, reason = check_blacklist("000001.SZ", {"name": "*ST 某某"})
        assert blocked is True
        assert "ST" in reason

    def test_blacklist_normal(self):
        blocked, reason = check_blacklist(
            "600519.SH",
            {"name": "贵州茅台", "list_status": "L", "avg_amount": 200000},
        )
        assert blocked is False
        assert reason == ""

    def test_blacklist_low_volume(self):
        blocked, reason = check_blacklist(
            "600001.SH",
            {"name": "普通股票", "list_status": "L", "avg_amount": 3000},
        )
        assert blocked is True
        assert "5000" in reason


class TestPositionLimit:
    def test_position_limit_core(self):
        assert check_position_limit("core") == 15.0

    def test_position_limit_satellite(self):
        assert check_position_limit("satellite") == 3.0


class TestStopLoss:
    def test_stop_loss_trigger(self):
        triggered, reason = check_stop_loss(100.0, 85.0, "core")
        assert triggered is True
        assert "15.0%" in reason

    def test_stop_loss_ok(self):
        triggered, reason = check_stop_loss(100.0, 95.0, "core")
        assert triggered is False
        assert reason == ""


class TestPortfolioDrawdown:
    def test_portfolio_drawdown(self):
        triggered, reason = check_portfolio_drawdown(-10.0)
        assert triggered is True
        assert "暂停" in reason

    def test_portfolio_drawdown_ok(self):
        triggered, reason = check_portfolio_drawdown(-5.0)
        assert triggered is False
