import pytest
from agents.state import MarketState, AgentOutput, CriticOutput, SignalOutput


def test_market_state_creation():
    state: MarketState = {"trade_date": "20260502", "ts_code": "000988.SZ", "stock_name": "华工科技"}
    assert state["ts_code"] == "000988.SZ"


def test_market_state_partial():
    state: MarketState = {"trade_date": "20260502"}
    assert "ts_code" not in state


def test_agent_output():
    out = AgentOutput(score=75.5, highlights=["营收增长"], risks=["应收账款高"], data_sources=["income"], summary="基本面良好")
    assert out.score == 75.5
    assert len(out.highlights) == 1


def test_agent_output_validation():
    with pytest.raises(Exception):
        AgentOutput(score=150)  # 超出 0-100 范围


def test_critic_output():
    out = CriticOutput(score=45, objections=["商誉过高"], worst_case="减值风险", verdict="reject")
    assert out.verdict == "reject"


def test_signal_output():
    sig = SignalOutput(
        ts_code="000988.SZ", direction="buy", confidence=0.8,
        position_pct=5.0, stop_loss=25.0, reasons=["CPO龙头"],
        data_sources=["daily"], critic_score=72, critic_objections=[]
    )
    assert sig.direction == "buy"
    assert sig.position_pct == 5.0


def test_signal_output_position_limit():
    with pytest.raises(Exception):
        SignalOutput(ts_code="x", direction="buy", confidence=0.5,
                     position_pct=20.0, stop_loss=10, critic_score=50)  # 超出 15% 上限
