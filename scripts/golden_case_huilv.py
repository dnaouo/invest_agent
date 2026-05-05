"""金标准案例 B：汇绿生态 001267 — 事件驱动 + 游资接力。
截断点 T=2025-10-28（陈小群等游资龙虎榜入场日）。
验收：Event + Flow Hot Money agent 识别游资入场信号。
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from harness.orchestrator import run_analysis
from session.notes import write_note

TS_CODE = "001267.SZ"
STOCK_NAME = "汇绿生态"
CUTOFF_DATE = "20251028"


def main():
    print("=" * 60)
    print(f"金标准案例 B：{STOCK_NAME}（{TS_CODE}）")
    print(f"截断点 T = {CUTOFF_DATE}")
    print("=" * 60)

    print("\n运行完整 10 agent 分析...")
    result = run_analysis(TS_CODE, CUTOFF_DATE, STOCK_NAME)

    event = result.get("event_analysis", {})
    flow_hot = result.get("flow_hot_money", {})
    critic = result.get("critic_review", {})
    signal = result.get("supervisor_signal", {})

    print(f"\n--- 各 Agent 评分 ---")
    for key in ["fundamental_score", "technical_score", "macro_themes",
                "event_analysis", "flow_institutional", "flow_hot_money",
                "risk_assessment", "backtest_result"]:
        score = result.get(key, {}).get("score", "N/A")
        print(f"  {key}: {score}")

    print(f"\n--- Event Agent ---")
    print(f"  Score: {event.get('score', 'N/A')}")
    print(f"  Events: {event.get('events', [])[:3]}")

    print(f"\n--- Flow Hot Money ---")
    print(f"  Score: {flow_hot.get('score', 'N/A')}")

    print(f"\n--- Critic ---")
    print(f"  Score: {critic.get('score', 'N/A')}")
    print(f"  Verdict: {critic.get('verdict', 'N/A')}")

    print(f"\n--- Supervisor Signal ---")
    print(f"  Direction: {signal.get('direction', 'N/A')}")
    print(f"  Confidence: {signal.get('confidence', 'N/A')}")
    print(f"  Position: {signal.get('position_pct', 'N/A')}%")

    note = f"# 金标准案例 B：{STOCK_NAME}\n\n"
    note += f"截断点：{CUTOFF_DATE}\n\n"
    note += f"## 结果\n{json.dumps(result, ensure_ascii=False, indent=2, default=str)[:3000]}\n"
    write_note(f"golden_huilv_{CUTOFF_DATE}", note)

    print(f"\n[DONE] 报告已写入 data/notes/")


if __name__ == "__main__":
    main()
