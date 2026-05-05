"""Tests for tools.llm_judge."""
import pytest
from unittest.mock import patch
from tools.llm_judge import judge_signal


def test_judge_signal_success():
    """mock call_kimi 返回评分 JSON，验证格式。"""
    mock_response = {
        "content": '{"fact_accuracy": 0.8, "data_citation": 0.7, "logic": 0.9, "risk_awareness": 0.6, "overall": 0.75}',
        "reasoning_content": None,
        "tool_calls": None,
        "usage": {"total_tokens": 500},
    }
    with patch("tools.llm_judge.call_kimi", return_value=mock_response):
        result = judge_signal({"signal": "buy", "reason": "PE低于历史均值"})

    assert result["overall"] == 0.75
    assert result["fact_accuracy"] == 0.8
    assert result["data_citation"] == 0.7
    assert result["logic"] == 0.9
    assert result["risk_awareness"] == 0.6
    assert "_parse_failed" not in result


def test_judge_signal_auto_overall():
    """当 LLM 未返回 overall 时，自动计算平均值。"""
    mock_response = {
        "content": '前置文字 {"fact_accuracy": 0.8, "data_citation": 0.6, "logic": 0.7, "risk_awareness": 0.5} 后置文字',
        "reasoning_content": None,
        "tool_calls": None,
        "usage": {"total_tokens": 500},
    }
    with patch("tools.llm_judge.call_kimi", return_value=mock_response):
        result = judge_signal({"signal": "hold"})

    assert result["overall"] == pytest.approx(0.65, abs=1e-9)
    assert "_parse_failed" not in result


def test_judge_signal_parse_failure():
    """mock 返回非 JSON，验证降级。"""
    mock_response = {
        "content": "这不是一个有效的 JSON 响应，无法解析。",
        "reasoning_content": None,
        "tool_calls": None,
        "usage": {"total_tokens": 100},
    }
    with patch("tools.llm_judge.call_kimi", return_value=mock_response):
        result = judge_signal({"signal": "sell"})

    assert result["overall"] == 0.5
    assert result["_parse_failed"] is True
    assert result["fact_accuracy"] == 0.5
    assert result["data_citation"] == 0.5
    assert result["logic"] == 0.5
    assert result["risk_awareness"] == 0.5
