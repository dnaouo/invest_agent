"""Tests for llm_clients.tier_router."""

from llm_clients.tier_router import get_tier_config


def test_supervisor_is_tier_a() -> None:
    cfg = get_tier_config("supervisor")
    assert cfg == {"thinking": True, "max_tokens": 32768}


def test_fund_is_tier_b_recall() -> None:
    cfg = get_tier_config("fund")
    assert cfg == {"thinking": False, "max_tokens": 8192}


def test_unknown_agent_defaults_to_b_recall() -> None:
    cfg = get_tier_config("nonexistent_agent")
    assert cfg == {"thinking": False, "max_tokens": 8192}
