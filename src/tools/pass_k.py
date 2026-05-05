"""pass^k 一致性检验 — 同一标的多次独立运行，检查方向一致性。"""
from __future__ import annotations
from harness.orchestrator import run_analysis


def run_pass_k(ts_code: str, trade_date: str, stock_name: str = "", k: int = 5, threshold: int = 4) -> dict:
    """跑 k 次独立分析，至少 threshold 次方向一致才算通过。"""
    directions = []
    for i in range(k):
        try:
            result = run_analysis(ts_code, trade_date, stock_name)
            signal = result.get("supervisor_signal", {})
            direction = signal.get("direction", "hold")
            directions.append(direction)
        except Exception:
            directions.append("error")

    from collections import Counter
    counts = Counter(directions)
    most_common_dir, most_common_count = counts.most_common(1)[0]
    consistency = most_common_count / k
    passed = most_common_count >= threshold

    return {
        "passed": passed,
        "directions": directions,
        "most_common": most_common_dir,
        "consistency": consistency,
        "k": k,
        "threshold": threshold,
    }
