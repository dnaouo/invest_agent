"""tests for tools/black_swan.py"""
from tools.black_swan import check_signal_anomaly, check_batch_anomaly, check_market_anomaly


def test_signal_anomaly_normal():
    signal = {"position_pct": 5}
    hist = [{"position_pct": i} for i in range(1, 101)]
    is_anomaly, reason = check_signal_anomaly(signal, hist)
    assert is_anomaly is False
    assert reason == ""


def test_signal_anomaly_extreme():
    signal = {"position_pct": 120}
    hist = [{"position_pct": i} for i in range(1, 101)]
    is_anomaly, reason = check_signal_anomaly(signal, hist)
    assert is_anomaly is True
    assert "99 分位" in reason


def test_batch_anomaly_too_many():
    signals = [{"direction": "buy", "position_pct": 5}] * 11
    is_anomaly, reason = check_batch_anomaly(signals)
    assert is_anomaly is True
    assert "11 条信号" in reason


def test_batch_anomaly_all_buy():
    signals = [{"direction": "buy"} for _ in range(4)]
    is_anomaly, reason = check_batch_anomaly(signals)
    assert is_anomaly is True
    assert "全 buy" in reason


def test_batch_anomaly_normal():
    signals = [
        {"direction": "buy"},
        {"direction": "sell"},
        {"direction": "hold"},
        {"direction": "buy"},
    ]
    is_anomaly, reason = check_batch_anomaly(signals)
    assert is_anomaly is False
    assert reason == ""


def test_market_anomaly_crash():
    is_anomaly, reason = check_market_anomaly(index_change_pct=-6.5)
    assert is_anomaly is True
    assert "黑天鹅" in reason


def test_market_anomaly_normal():
    is_anomaly, reason = check_market_anomaly(index_change_pct=-1.2)
    assert is_anomaly is False
    assert reason == ""
