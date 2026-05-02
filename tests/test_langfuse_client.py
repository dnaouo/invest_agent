"""Tests for observability.langfuse_client — 重点测试降级行为。"""

from unittest.mock import MagicMock

import pytest

import observability.langfuse_client as mod


@pytest.fixture(autouse=True)
def _reset():
    mod._langfuse = None
    mod._disabled = False
    yield
    mod._langfuse = None
    mod._disabled = False


def test_graceful_degradation_when_not_configured():
    result = mod.trace_llm_call("fund", "input", "output", tokens=100)
    assert result is None


def test_graceful_degradation_get_trace_url():
    result = mod.get_trace_url("some-id")
    assert result is None


def test_trace_with_mock_langfuse():
    mock_lf = MagicMock()
    mock_trace = MagicMock()
    mock_trace.id = "trace-123"
    mock_lf.trace.return_value = mock_trace

    mod._langfuse = mock_lf

    result = mod.trace_llm_call("fund", "input", "output", tokens=100)
    assert result == "trace-123"
    mock_lf.trace.assert_called_once()
    mock_trace.generation.assert_called_once()


def test_disabled_flag_prevents_retry():
    mod.trace_llm_call("fund", "input", "output")
    assert mod._disabled is True
    mod.trace_llm_call("fund", "input2", "output2")
    assert mod._disabled is True


def test_flush_when_disabled():
    mod._disabled = True
    mod.flush()  # should not raise
