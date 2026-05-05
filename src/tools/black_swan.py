"""黑天鹅检测 — 异常信号强制人工审核。"""
from __future__ import annotations


def check_signal_anomaly(signal: dict, historical_signals: list[dict]) -> tuple[bool, str]:
    """检查单个信号是否异常。"""
    position_pct = signal.get("position_pct", 0)
    if historical_signals:
        hist_positions = sorted([s.get("position_pct", 0) for s in historical_signals])
        p99_idx = int(len(hist_positions) * 0.99)
        p99 = hist_positions[min(p99_idx, len(hist_positions) - 1)]
        if position_pct > p99 and p99 > 0:
            return True, f"仓位 {position_pct}% 超过历史 99 分位 {p99}%"
    return False, ""


def check_batch_anomaly(signals: list[dict]) -> tuple[bool, str]:
    """检查一批信号是否异常。"""
    if len(signals) > 10:
        return True, f"单日 {len(signals)} 条信号 > 10 条上限"
    directions = [s.get("direction") for s in signals if s.get("direction") != "hold"]
    if len(directions) >= 3:
        if all(d == "buy" for d in directions):
            return True, "所有信号方向一致（全 buy），可能存在系统性偏差"
        if all(d == "sell" for d in directions):
            return True, "所有信号方向一致（全 sell），可能存在系统性偏差"
    return False, ""


def check_market_anomaly(index_change_pct: float, limit_up_ratio: float = 0, limit_down_ratio: float = 0) -> tuple[bool, str]:
    """检查市场是否异常。"""
    if index_change_pct < -5:
        return True, f"指数跌幅 {index_change_pct:.1f}% > 5%，疑似黑天鹅"
    if limit_down_ratio > 0.2:
        return True, f"跌停股占比 {limit_down_ratio:.0%} > 20%"
    if limit_up_ratio > 0.2:
        return True, f"涨停股占比 {limit_up_ratio:.0%} > 20%，市场极端"
    return False, ""
