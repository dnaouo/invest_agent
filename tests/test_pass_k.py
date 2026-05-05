"""Tests for tools/pass_k.py — pass^k 一致性检验。"""
from unittest.mock import patch


@patch("tools.pass_k.run_analysis")
def test_pass_k_consistent(mock_run):
    """5 次都返回 buy，验证 passed=True。"""
    mock_run.return_value = {"supervisor_signal": {"direction": "buy"}}

    from tools.pass_k import run_pass_k
    result = run_pass_k("000001.SZ", "20260502", k=5, threshold=4)

    assert result["passed"] is True
    assert result["most_common"] == "buy"
    assert result["consistency"] == 1.0
    assert result["directions"] == ["buy"] * 5


@patch("tools.pass_k.run_analysis")
def test_pass_k_inconsistent(mock_run):
    """3 次 buy + 2 次 hold，验证 passed=False（threshold=4）。"""
    mock_run.side_effect = [
        {"supervisor_signal": {"direction": "buy"}},
        {"supervisor_signal": {"direction": "buy"}},
        {"supervisor_signal": {"direction": "buy"}},
        {"supervisor_signal": {"direction": "hold"}},
        {"supervisor_signal": {"direction": "hold"}},
    ]

    from tools.pass_k import run_pass_k
    result = run_pass_k("000001.SZ", "20260502", k=5, threshold=4)

    assert result["passed"] is False
    assert result["most_common"] == "buy"
    assert result["consistency"] == 0.6


@patch("tools.pass_k.run_analysis")
def test_pass_k_with_errors(mock_run):
    """2 次成功 + 3 次异常，验证 passed=False。"""
    mock_run.side_effect = [
        {"supervisor_signal": {"direction": "buy"}},
        {"supervisor_signal": {"direction": "buy"}},
        RuntimeError("timeout"),
        RuntimeError("timeout"),
        RuntimeError("timeout"),
    ]

    from tools.pass_k import run_pass_k
    result = run_pass_k("000001.SZ", "20260502", k=5, threshold=4)

    assert result["passed"] is False
    assert result["directions"].count("error") == 3
    assert result["directions"].count("buy") == 2
