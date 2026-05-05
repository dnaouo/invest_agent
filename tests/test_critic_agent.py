"""Tests for agents.critic — mock Kimi。"""
from unittest.mock import patch, MagicMock
import json

import pytest

from agents.critic import critic_node, _format_prior_analysis


def test_format_prior_analysis_with_data():
    state = {
        "ts_code": "000988.SZ",
        "fundamental_score": {"score": 75, "summary": "良好"},
    }
    text = _format_prior_analysis(state)
    assert "基本面分析" in text
    assert "75" in text


def test_format_prior_analysis_empty():
    state = {"ts_code": "000988.SZ"}
    text = _format_prior_analysis(state)
    assert "暂无" in text


@patch("agents.critic.call_kimi")
def test_critic_node_pass(mock_kimi):
    mock_kimi.return_value = {
        "content": json.dumps({
            "score": 72,
            "objections": ["估值偏高"],
            "worst_case": "回调 15%",
            "verdict": "pass"
        }),
        "reasoning_content": "thinking...",
        "tool_calls": None,
        "usage": MagicMock(),
    }

    state = {
        "ts_code": "000988.SZ",
        "stock_name": "华工科技",
        "fundamental_score": {"score": 78, "summary": "基本面良好"},
    }
    result = critic_node(state)

    assert "critic_review" in result
    assert result["critic_review"]["verdict"] == "pass"
    assert result["critic_review"]["score"] == 72


@patch("agents.critic.call_kimi")
def test_critic_node_reject(mock_kimi):
    mock_kimi.return_value = {
        "content": json.dumps({
            "score": 35,
            "objections": ["数据严重不足", "逻辑漏洞"],
            "worst_case": "跌 30%",
            "verdict": "reject"
        }),
        "reasoning_content": None,
        "tool_calls": None,
        "usage": MagicMock(),
    }

    state = {"ts_code": "000988.SZ", "fundamental_score": {"score": 60}}
    result = critic_node(state)

    assert result["critic_review"]["verdict"] == "reject"
    assert result["critic_review"]["score"] == 35


@patch("agents.critic.call_kimi")
def test_critic_node_parse_failure(mock_kimi):
    mock_kimi.return_value = {
        "content": "无法解析的响应",
        "reasoning_content": None,
        "tool_calls": None,
        "usage": MagicMock(),
    }

    state = {"ts_code": "000988.SZ"}
    result = critic_node(state)

    assert result["critic_review"]["verdict"] == "reject"
    assert "解析失败" in result["critic_review"]["objections"][0]


@patch("agents.critic.call_kimi")
def test_critic_uses_tier_a(mock_kimi):
    """验证 critic 使用 Tier A 配置（thinking 开）。"""
    mock_kimi.return_value = {
        "content": json.dumps({"score": 70, "objections": [], "worst_case": "", "verdict": "pass"}),
        "reasoning_content": None,
        "tool_calls": None,
        "usage": MagicMock(),
    }

    state = {"ts_code": "000988.SZ"}
    critic_node(state)

    call_kwargs = mock_kimi.call_args
    assert call_kwargs.kwargs.get("thinking") is True or call_kwargs[1].get("thinking") is True
