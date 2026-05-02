"""Tests for llm_clients.kimi_sync — all API calls are mocked."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import llm_clients.kimi_sync as _mod
from llm_clients.kimi_sync import call_kimi


@pytest.fixture(autouse=True)
def _reset_client():
    """每个测试前后重置懒加载的 _client 实例。"""
    _mod._client = None
    yield
    _mod._client = None


def _make_mock_response(
    content: str = "hello",
    reasoning_content: str | None = None,
    tool_calls: list | None = None,
) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    msg.reasoning_content = reasoning_content
    msg.tool_calls = tool_calls

    choice = MagicMock()
    choice.message = msg

    usage = MagicMock()
    usage.prompt_tokens = 10
    usage.completion_tokens = 5
    usage.total_tokens = 15

    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage
    return resp


@patch("llm_clients.kimi_sync.OpenAI")
def test_call_kimi_simple_string(mock_openai_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = _make_mock_response()

    result = call_kimi("你好")

    create_call = mock_client.chat.completions.create
    create_call.assert_called_once()
    call_kwargs = create_call.call_args
    sent_messages = call_kwargs.kwargs["messages"]
    assert sent_messages == [{"role": "user", "content": "你好"}]

    assert result["content"] == "hello"
    assert result["reasoning_content"] is None
    assert result["tool_calls"] is None
    assert result["usage"] is not None


@patch("llm_clients.kimi_sync.OpenAI")
def test_call_kimi_thinking_min_tokens(mock_openai_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = _make_mock_response()

    call_kimi("test", thinking=True, max_tokens=1000)

    call_kwargs = mock_client.chat.completions.create.call_args
    assert call_kwargs.kwargs["max_tokens"] == 16000


def test_call_kimi_invalid_tool_choice() -> None:
    with pytest.raises(ValueError, match="tool_choice must be 'auto' or 'none'"):
        call_kimi("test", tool_choice="required")


@patch("llm_clients.kimi_sync.OpenAI")
def test_call_kimi_with_thinking_extra_body(mock_openai_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = _make_mock_response(
        reasoning_content="let me think..."
    )

    result = call_kimi("test", thinking=True)

    call_kwargs = mock_client.chat.completions.create.call_args
    extra_body = call_kwargs.kwargs["extra_body"]
    assert extra_body == {"thinking": {"type": "enabled"}}
    assert result["reasoning_content"] == "let me think..."
