"""Kimi K2.6 synchronous client — thin wrapper over OpenAI-compatible API."""

from __future__ import annotations

from typing import Any

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from requests.exceptions import ConnectionError as ReqConnectionError

from vault.proxy import get_credential

_BASE_URL = "https://api.moonshot.cn/v1"

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=get_credential("moonshot"),
            base_url=_BASE_URL,
            timeout=600.0,
        )
    return _client


_VALID_TOOL_CHOICES = {"auto", "none"}
_THINKING_MIN_TOKENS = 16_000


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(min=2, max=30),
    retry=retry_if_exception_type((
        APIConnectionError, APITimeoutError, RateLimitError,
        ReqConnectionError, ConnectionError,
    )),
    reraise=True,
)
def call_kimi(
    messages: list[dict] | str,
    model: str = "kimi-k2.6",
    thinking: bool = False,
    max_tokens: int = 8192,
    tools: list[dict] | None = None,
    tool_choice: str | None = None,
) -> dict[str, Any]:
    """调用 Kimi K2.6，返回 {"content": str, "reasoning_content": str | None, "tool_calls": list | None, "usage": dict}"""

    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]

    if tool_choice is not None and tool_choice not in _VALID_TOOL_CHOICES:
        raise ValueError(
            f"tool_choice must be 'auto' or 'none', got {tool_choice!r}"
        )

    if thinking and max_tokens < _THINKING_MIN_TOKENS:
        max_tokens = _THINKING_MIN_TOKENS

    extra_body: dict[str, Any] = {
        "thinking": {"type": "enabled" if thinking else "disabled"},
    }

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "extra_body": extra_body,
    }
    if tools is not None:
        kwargs["tools"] = tools
    if tool_choice is not None:
        kwargs["tool_choice"] = tool_choice

    client = _get_client()
    response = client.chat.completions.create(**kwargs)

    msg = response.choices[0].message
    return {
        "content": msg.content,
        "reasoning_content": getattr(msg, "reasoning_content", None),
        "tool_calls": msg.tool_calls,
        "usage": response.usage,
    }
