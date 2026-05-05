from harness.fallback import safe_run_node, is_all_degraded, emergency_hold


def test_drill_api_failure():
    def bad(state): raise ConnectionError("fail")
    result = safe_run_node(bad, {}, "fundamental_score")
    assert result["fundamental_score"]["_degraded"] is True


def test_drill_llm_timeout():
    def bad(state): raise TimeoutError("timeout")
    result = safe_run_node(bad, {}, "critic_review")
    assert result["critic_review"]["_degraded"] is True
    assert result["critic_review"]["verdict"] == "reject"


def test_drill_total_failure():
    state = {k: {"score": 50, "_degraded": True} for k in ["fundamental_score", "technical_score", "macro_themes", "event_analysis"]}
    assert is_all_degraded(state) is True
    hold = emergency_hold()
    assert hold["supervisor_signal"]["direction"] == "hold"


def test_drill_partial_ok():
    state = {"fundamental_score": {"score": 70}, "technical_score": {"score": 50, "_degraded": True},
             "macro_themes": {"score": 60}, "event_analysis": {"score": 50, "_degraded": True}}
    assert is_all_degraded(state) is False
