"""Tests for agents.supervisor — 动态加权 + critic 否决。"""
from unittest.mock import patch, MagicMock
import json

from agents.supervisor import _compute_weighted_score, supervisor_node


def test_compute_weighted_score_fundamental():
    state = {"fundamental_score": {"score": 80}, "event_analysis": {"score": 40}}
    info = _compute_weighted_score(state)
    assert info["type"] == "fundamental_driven"
    assert info["weighted_score"] > 0


def test_compute_weighted_score_event():
    state = {"fundamental_score": {"score": 40}, "event_analysis": {"score": 80}}
    info = _compute_weighted_score(state)
    assert info["type"] == "event_driven"


def test_compute_weighted_score_default():
    state = {}
    info = _compute_weighted_score(state)
    assert info["weighted_score"] == 50.0


@patch("agents.supervisor.call_kimi")
def test_supervisor_critic_reject_forces_hold(mock_kimi):
    mock_kimi.return_value = {
        "content": json.dumps({"direction": "buy", "confidence": 0.8, "position_pct": 5.0, "reasons": ["test"], "summary": "ok"}),
        "reasoning_content": None, "tool_calls": None, "usage": MagicMock(),
    }
    state = {
        "ts_code": "000988.SZ", "stock_name": "test",
        "fundamental_score": {"score": 70},
        "critic_review": {"score": 40, "verdict": "reject", "objections": ["bad"]},
    }
    result = supervisor_node(state)
    sig = result["supervisor_signal"]
    assert sig["direction"] == "hold"
    assert sig["confidence"] == 0.0
    assert "Critic 否决" in str(sig.get("reasons", []))
