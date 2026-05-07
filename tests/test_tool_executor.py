"""Tests for tools/tool_executor.py"""
from unittest.mock import patch, MagicMock
import pytest


def _make_tool_call(tc_id, name, arguments):
    """构造模拟的 tool_call 对象（dict 形式）。"""
    return {
        "id": tc_id,
        "function": {"name": name, "arguments": arguments},
    }


@patch("tools.tool_executor.call_kimi")
def test_no_tool_call(mock_kimi):
    """LLM 直接返回 content 不调 tool。"""
    mock_kimi.return_value = {
        "content": "分析完成：该股票基本面良好。",
        "reasoning_content": None,
        "tool_calls": None,
    }

    from tools.tool_executor import run_agent_with_tools

    result = run_agent_with_tools(
        system_prompt="你是分析师",
        user_message="分析000001.SZ",
        tools=[],
        tool_functions={},
        tier_config={"model": "kimi-k2.6", "max_tokens": 4096},
    )

    assert result["content"] == "分析完成：该股票基本面良好。"
    assert result["tool_calls_made"] == []


@patch("tools.tool_executor.call_kimi")
def test_one_tool_call(mock_kimi):
    """LLM 调 1 次 tool 后返回最终 content。"""
    mock_kimi.side_effect = [
        {
            "content": "",
            "reasoning_content": "需要查研报",
            "tool_calls": [_make_tool_call("tc_1", "search_reports", '{"keyword": "光模块"}')],
        },
        {
            "content": "根据研报，光模块行业前景看好。",
            "reasoning_content": None,
            "tool_calls": None,
        },
    ]

    def fake_search(keyword):
        return f"找到了关于{keyword}的3篇研报"

    from tools.tool_executor import run_agent_with_tools

    result = run_agent_with_tools(
        system_prompt="你是分析师",
        user_message="分析光模块行业",
        tools=[{"type": "function", "function": {"name": "search_reports"}}],
        tool_functions={"search_reports": fake_search},
        tier_config={"model": "kimi-k2.6", "max_tokens": 4096},
    )

    assert "光模块" in result["content"]
    assert len(result["tool_calls_made"]) == 1
    assert result["tool_calls_made"][0]["name"] == "search_reports"
    assert "光模块" in result["tool_calls_made"][0]["result"]


@patch("tools.tool_executor.call_kimi")
def test_max_rounds(mock_kimi):
    """超过 max_rounds 限制，返回最后内容。"""
    mock_kimi.return_value = {
        "content": "还需要更多数据",
        "reasoning_content": None,
        "tool_calls": [_make_tool_call("tc_x", "search_news", '{"keyword": "test"}')],
    }

    def fake_news(keyword):
        return "一些新闻"

    from tools.tool_executor import run_agent_with_tools

    result = run_agent_with_tools(
        system_prompt="你是分析师",
        user_message="分析",
        tools=[{"type": "function", "function": {"name": "search_news"}}],
        tool_functions={"search_news": fake_news},
        tier_config={"model": "kimi-k2.6", "max_tokens": 4096},
        max_rounds=2,
    )

    assert len(result["tool_calls_made"]) == 2
    assert mock_kimi.call_count == 2
