"""Tests for harness.orchestrator — mock all agent LLM calls."""
from unittest.mock import patch, MagicMock
import json


def _mock_kimi_response(result_dict: dict):
    return {
        "content": json.dumps(result_dict, ensure_ascii=False),
        "reasoning_content": None,
        "tool_calls": None,
        "usage": MagicMock(),
    }


def _mock_tushare_ok(data=None):
    return {"status": "ok", "data": data or [{"test": 1}]}


@patch("agents.supervisor.call_kimi")
@patch("agents.critic.call_kimi")
@patch("agents.backtest.call_kimi")
@patch("agents.risk.call_kimi")
@patch("agents.flow_hot_money.call_kimi")
@patch("agents.flow_institutional.call_kimi")
@patch("agents.event.call_kimi")
@patch("agents.tech.call_kimi")
@patch("agents.fund.call_kimi")
@patch("agents.macro.call_kimi")
@patch("agents.macro.akshare_client")
@patch("agents.macro.tushare_client")
@patch("agents.fund.tushare_client")
@patch("agents.tech.tushare_client")
@patch("agents.event.tushare_client")
@patch("agents.flow_institutional.tushare_client")
@patch("agents.flow_hot_money.tushare_client")
@patch("agents.risk.tushare_client")
@patch("agents.backtest.tushare_client")
def test_full_graph(
    mock_bt_ts, mock_risk_ts, mock_fh_ts, mock_fi_ts,
    mock_ev_ts, mock_tech_ts, mock_fund_ts,
    mock_macro_ts, mock_macro_ak,
    mock_macro_kimi, mock_fund_kimi, mock_tech_kimi,
    mock_event_kimi, mock_fi_kimi, mock_fh_kimi,
    mock_risk_kimi, mock_bt_kimi, mock_critic_kimi,
    mock_sup_kimi,
):
    """验证完整 10 节点图能跑通。"""
    for mock_ts in [mock_bt_ts, mock_risk_ts, mock_fh_ts, mock_fi_ts,
                    mock_ev_ts, mock_tech_ts, mock_fund_ts, mock_macro_ts]:
        for attr in dir(mock_ts):
            if attr.startswith("get_"):
                getattr(mock_ts, attr).return_value = _mock_tushare_ok()

    mock_macro_ak.get_cls_news.return_value = _mock_tushare_ok()
    mock_macro_ak.get_jin10_news.return_value = _mock_tushare_ok()

    mock_macro_kimi.return_value = _mock_kimi_response({"score": 70, "top_themes": [], "data_sources": [], "summary": "ok"})
    mock_fund_kimi.return_value = _mock_kimi_response({"score": 75, "highlights": [], "risks": [], "data_sources": [], "summary": "ok"})
    mock_tech_kimi.return_value = _mock_kimi_response({"score": 65, "pattern": "consolidation", "data_sources": [], "summary": "ok"})
    mock_event_kimi.return_value = _mock_kimi_response({"score": 60, "events": [], "data_sources": [], "summary": "ok"})
    mock_fi_kimi.return_value = _mock_kimi_response({"score": 55, "north_flow_trend": "neutral", "data_sources": [], "summary": "ok"})
    mock_fh_kimi.return_value = _mock_kimi_response({"score": 50, "hot_money_trades": [], "data_sources": [], "summary": "ok"})
    mock_risk_kimi.return_value = _mock_kimi_response({"score": 70, "risk_flags": [], "position_suggestion": {"max_pct": 5}, "data_sources": [], "summary": "ok"})
    mock_bt_kimi.return_value = _mock_kimi_response({"score": 60, "sharpe": 1.2, "max_drawdown": 0.15, "data_sources": [], "summary": "ok"})
    mock_critic_kimi.return_value = _mock_kimi_response({"score": 65, "objections": ["minor"], "worst_case": "10%", "verdict": "pass"})
    mock_sup_kimi.return_value = _mock_kimi_response({"direction": "buy", "confidence": 0.7, "position_pct": 5.0, "stop_loss": 25.0, "reasons": ["test"], "summary": "ok"})

    from harness.orchestrator import run_analysis
    result = run_analysis("000988.SZ", "20260430", "华工科技")

    assert "fundamental_score" in result
    assert "macro_themes" in result
    assert "technical_score" in result
    assert "event_analysis" in result
    assert "critic_review" in result
    assert "supervisor_signal" in result
    assert result["supervisor_signal"]["direction"] == "buy"
