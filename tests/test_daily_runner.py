"""Tests for harness.daily_runner."""
from unittest.mock import patch, MagicMock
import json


@patch("harness.daily_runner.emit_event")
@patch("harness.daily_runner.write_note")
@patch("harness.daily_runner.save_handoff")
@patch("harness.daily_runner.get_portfolio", return_value=None)
@patch("harness.daily_runner.execute_signal", return_value=None)
@patch("harness.daily_runner.update_portfolio")
@patch("harness.daily_runner.run_analysis")
def test_run_daily_basic(mock_analysis, mock_update, mock_execute, mock_get_port, mock_save, mock_note, mock_emit):
    from harness.daily_runner import run_daily
    from sandboxes.execute.paper_trading import PaperPortfolio

    mock_analysis.return_value = {"supervisor_signal": {"direction": "hold", "confidence": 0}}
    mock_update.return_value = PaperPortfolio(date="20260430")

    result = run_daily("20260430", stock_pool=["000988.SZ"])

    assert result["date"] == "20260430"
    assert len(result["signals"]) == 1
    mock_analysis.assert_called_once()
    mock_save.assert_called_once()


@patch("harness.daily_runner.emit_event")
@patch("harness.daily_runner.write_note")
@patch("harness.daily_runner.save_handoff")
@patch("harness.daily_runner.get_portfolio", return_value=None)
@patch("harness.daily_runner.execute_signal", return_value=None)
@patch("harness.daily_runner.update_portfolio")
@patch("harness.daily_runner.run_analysis")
def test_run_daily_analysis_error(mock_analysis, mock_update, mock_execute, mock_get_port, mock_save, mock_note, mock_emit):
    from harness.daily_runner import run_daily
    from sandboxes.execute.paper_trading import PaperPortfolio

    mock_analysis.side_effect = RuntimeError("API down")
    mock_update.return_value = PaperPortfolio(date="20260430")

    result = run_daily("20260430", stock_pool=["000988.SZ"])

    assert result["signals"][0].get("direction") == "hold"
    assert "_error" in result["signals"][0]
