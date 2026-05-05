"""金标准案例 A：华工科技 000988 — 基本面驱动 + 题材共振。
截断点 T=2026-01-07（800G LPO 海外交付公告日）。
验收：T+10 内输出 watchlist 信号 + 仓位建议。
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from harness.orchestrator import run_analysis
from tools.time_slice import slice_data
from session.notes import write_note

TS_CODE = "000988.SZ"
STOCK_NAME = "华工科技"
CUTOFF_DATE = "20260107"


def main():
    print("=" * 60)
    print(f"金标准案例 A：{STOCK_NAME}（{TS_CODE}）")
    print(f"截断点 T = {CUTOFF_DATE}")
    print("=" * 60)

    print("\n运行完整 10 agent 分析（数据截断到 T-1）...")
    result = run_analysis(TS_CODE, CUTOFF_DATE, STOCK_NAME)

    fund = result.get("fundamental_score", {})
    macro = result.get("macro_themes", {})
    event = result.get("event_analysis", {})
    critic = result.get("critic_review", {})
    signal = result.get("supervisor_signal", {})

    print(f"\n--- 各 Agent 评分 ---")
    for key in ["fundamental_score", "technical_score", "macro_themes",
                "event_analysis", "flow_institutional", "flow_hot_money",
                "risk_assessment", "backtest_result"]:
        score = result.get(key, {}).get("score", "N/A")
        print(f"  {key}: {score}")

    print(f"\n--- Critic ---")
    print(f"  Score: {critic.get('score', 'N/A')}")
    print(f"  Verdict: {critic.get('verdict', 'N/A')}")

    print(f"\n--- Supervisor Signal ---")
    print(f"  Direction: {signal.get('direction', 'N/A')}")
    print(f"  Confidence: {signal.get('confidence', 'N/A')}")
    print(f"  Position: {signal.get('position_pct', 'N/A')}%")

    note = f"# 金标准案例 A：{STOCK_NAME}\n\n"
    note += f"截断点：{CUTOFF_DATE}\n\n"
    note += f"## 结果\n{json.dumps(result, ensure_ascii=False, indent=2, default=str)[:3000]}\n"
    write_note(f"golden_huagong_{CUTOFF_DATE}", note)

    print(f"\n[DONE] 报告已写入 data/notes/")


if __name__ == "__main__":
    main()
