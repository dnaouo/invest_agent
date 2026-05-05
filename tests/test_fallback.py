"""Tests for harness/fallback.py — 安全降级机制。"""
from harness.fallback import safe_run_node, is_all_degraded, emergency_hold


def test_safe_run_node_success():
    """正常节点执行成功，直接返回结果。"""
    def good_node(state):
        return {"fundamental_score": {"score": 80, "summary": "good"}}

    result = safe_run_node(good_node, {"ts_code": "000001.SZ"}, "fundamental_score")
    assert result == {"fundamental_score": {"score": 80, "summary": "good"}}


def test_safe_run_node_failure():
    """节点抛异常，返回降级默认值且含 _degraded=True。"""
    def bad_node(state):
        raise RuntimeError("API timeout")

    result = safe_run_node(bad_node, {"ts_code": "000001.SZ"}, "fundamental_score")
    assert "fundamental_score" in result
    score = result["fundamental_score"]
    assert score["_degraded"] is True
    assert "API timeout" in score["_error"]
    assert score["score"] == 50


def test_is_all_degraded_true():
    """4 个关键 agent 都降级时返回 True。"""
    state = {
        "fundamental_score": {"score": 50, "_degraded": True},
        "technical_score": {"score": 50, "_degraded": True},
        "macro_themes": {"score": 50, "_degraded": True},
        "event_analysis": {"score": 50, "_degraded": True},
    }
    assert is_all_degraded(state) is True


def test_is_all_degraded_false():
    """有 agent 正常时返回 False。"""
    state = {
        "fundamental_score": {"score": 80},
        "technical_score": {"score": 50, "_degraded": True},
        "macro_themes": {"score": 50, "_degraded": True},
        "event_analysis": {"score": 50, "_degraded": True},
    }
    assert is_all_degraded(state) is False


def test_emergency_hold():
    """验证紧急输出格式。"""
    result = emergency_hold()
    signal = result["supervisor_signal"]
    assert signal["direction"] == "hold"
    assert signal["confidence"] == 0.0
    assert signal["position_pct"] == 0.0
    assert signal["_emergency"] is True
    assert len(signal["reasons"]) > 0
