"""安全降级机制 — 单 agent 失败不崩溃。"""
from __future__ import annotations
import logging
import traceback

logger = logging.getLogger(__name__)

_DEFAULT_SCORES = {
    "fundamental_score": {"score": 50, "highlights": [], "risks": ["agent 降级：使用默认值"], "data_sources": [], "summary": "降级"},
    "technical_score": {"score": 50, "pattern": "unknown", "data_sources": [], "summary": "降级"},
    "macro_themes": {"score": 50, "top_themes": [], "data_sources": [], "summary": "降级"},
    "event_analysis": {"score": 50, "events": [], "data_sources": [], "summary": "降级"},
    "flow_institutional": {"score": 50, "north_flow_trend": "unknown", "data_sources": [], "summary": "降级"},
    "flow_hot_money": {"score": 50, "hot_money_trades": [], "data_sources": [], "summary": "降级"},
    "risk_assessment": {"score": 50, "risk_flags": ["降级"], "position_suggestion": {"max_pct": 0}, "data_sources": [], "summary": "降级"},
    "backtest_result": {"score": 50, "sharpe": 0, "max_drawdown": 0, "data_sources": [], "summary": "降级"},
    "critic_review": {"score": 50, "objections": ["critic 降级"], "worst_case": "无法评估", "verdict": "reject"},
    "supervisor_signal": {"direction": "hold", "confidence": 0, "position_pct": 0, "reasons": ["系统降级"], "summary": "降级"},
}


def safe_run_node(node_func, state: dict, fallback_key: str) -> dict:
    """安全执行 agent 节点。失败时返回降级默认值。"""
    try:
        result = node_func(state)
        return result
    except Exception as e:
        logger.error("Agent %s failed: %s\n%s", fallback_key, e, traceback.format_exc())
        default = dict(_DEFAULT_SCORES.get(fallback_key, {"score": 50, "summary": "降级"}))
        default["_degraded"] = True
        default["_error"] = str(e)
        return {fallback_key: default}


def is_all_degraded(state: dict) -> bool:
    """检查是否所有关键 agent 都降级了。"""
    keys = ["fundamental_score", "technical_score", "macro_themes", "event_analysis"]
    degraded = sum(1 for k in keys if state.get(k, {}).get("_degraded", False))
    return degraded >= len(keys)


def emergency_hold() -> dict:
    """全链路不可恢复时的紧急输出。"""
    return {
        "supervisor_signal": {
            "direction": "hold",
            "confidence": 0.0,
            "position_pct": 0.0,
            "reasons": ["全链路降级，今日不操作，持仓不变"],
            "summary": "系统紧急降级",
            "_emergency": True,
        }
    }
