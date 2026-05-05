"""Tests for paper trading system using temp file SQLite."""
import pytest
from sandboxes.execute.paper_trading import (
    PaperPortfolio,
    PaperTrade,
    execute_signal,
    get_portfolio,
    get_trade_history,
    update_portfolio,
)


@pytest.fixture()
def db_path(tmp_path):
    return str(tmp_path / "test_paper.sqlite")


@pytest.fixture()
def portfolio():
    return PaperPortfolio(date="20250501", cash=1_000_000.0, total_value=1_000_000.0)


def test_execute_signal_buy(portfolio, db_path):
    signal = {
        "direction": "buy",
        "ts_code": "000001.SZ",
        "stop_loss": 10.0,
        "position_pct": 10,
        "confidence": 0.8,
        "critic_score": 75,
    }
    trade = execute_signal(signal, portfolio, "20250502", db_path=db_path)
    assert trade is not None
    assert trade.direction == "buy"
    assert trade.ts_code == "000001.SZ"
    assert trade.price == 10.0
    assert trade.quantity == 10000
    assert trade.signal_confidence == 0.8
    assert trade.critic_score == 75


def test_execute_signal_hold(portfolio, db_path):
    signal = {"direction": "hold", "ts_code": "000001.SZ"}
    trade = execute_signal(signal, portfolio, "20250502", db_path=db_path)
    assert trade is None


def test_update_portfolio(portfolio, db_path):
    trade = PaperTrade(
        date="20250502", ts_code="000001.SZ",
        direction="buy", price=10.0, quantity=1000,
        position_pct=1.0,
    )
    updated = update_portfolio(portfolio, [trade], "20250502", db_path=db_path)
    assert updated.cash == pytest.approx(990_000.0)
    assert len(updated.positions) == 1
    assert updated.positions[0]["ts_code"] == "000001.SZ"
    assert updated.total_value == pytest.approx(1_000_000.0)


def test_get_portfolio(portfolio, db_path):
    trade = PaperTrade(
        date="20250502", ts_code="600519.SH",
        direction="buy", price=50.0, quantity=200,
        position_pct=1.0,
    )
    update_portfolio(portfolio, [trade], "20250502", db_path=db_path)
    loaded = get_portfolio("20250502", db_path=db_path)
    assert loaded is not None
    assert loaded.date == "20250502"
    assert loaded.cash == pytest.approx(990_000.0)
    assert len(loaded.positions) == 1


def test_get_trade_history(portfolio, db_path):
    signal1 = {
        "direction": "buy", "ts_code": "000001.SZ",
        "stop_loss": 10.0, "position_pct": 5, "confidence": 0.7,
    }
    signal2 = {
        "direction": "buy", "ts_code": "600519.SH",
        "stop_loss": 50.0, "position_pct": 3, "confidence": 0.6,
    }
    execute_signal(signal1, portfolio, "20250502", db_path=db_path)
    execute_signal(signal2, portfolio, "20250503", db_path=db_path)
    history = get_trade_history("20250501", "20250510", db_path=db_path)
    assert len(history) == 2
    assert history[0].date == "20250502"
    assert history[1].date == "20250503"
