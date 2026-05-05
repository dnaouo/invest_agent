"""Phase 1b 验证脚本：连续 5 个交易日运行分析 + handoff 续跑。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from harness.orchestrator import run_analysis
from harness.handoff import HandoffArtifact, save_handoff, load_handoff
from session.notes import write_note

TRADE_DATES = ["20260424", "20260425", "20260428", "20260429", "20260430"]
TS_CODE = "000988.SZ"
STOCK_NAME = "华工科技"


def main():
    print("=" * 60)
    print(f"Phase 1b 验证：{STOCK_NAME} 连续 5 日分析 + handoff")
    print("=" * 60)

    reject_count = 0

    for i, date in enumerate(TRADE_DATES):
        print(f"\n--- Day {i+1}: {date} ---")

        prev_handoff = load_handoff(TRADE_DATES[i-1]) if i > 0 else None
        if prev_handoff:
            print(f"  [HANDOFF] 加载前日交付物：{len(prev_handoff.pending_signals)} 条待确认信号")

        result = run_analysis(TS_CODE, date, STOCK_NAME)

        fund = result.get("fundamental_score", {})
        critic = result.get("critic_review", {})
        signal = result.get("supervisor_signal", {})

        print(f"  Fund score: {fund.get('score', 'N/A')}")
        print(f"  Critic score: {critic.get('score', 'N/A')} ({critic.get('verdict', 'N/A')})")
        print(f"  Signal: {signal.get('direction', 'N/A')} @ {signal.get('confidence', 0):.0%} conf, {signal.get('position_pct', 0)}% position")

        if critic.get("verdict") == "reject":
            reject_count += 1

        artifact = HandoffArtifact(
            date=date,
            positions=[{"ts_code": TS_CODE, "pct": signal.get("position_pct", 0)}] if signal.get("direction") == "buy" else [],
            pending_signals=[signal] if signal.get("direction") != "hold" else [],
            learnings=critic.get("objections", [])[:2],
            focus_themes=fund.get("highlights", [])[:2],
            blacklist_today=[],
        )
        save_handoff(artifact)

        note = f"# {STOCK_NAME} {date}\nSignal: {signal.get('direction')}\n"
        write_note(date, note)

    total = len(TRADE_DATES)
    reject_rate = reject_count / total * 100
    print(f"\n--- 统计 ---")
    print(f"  总天数: {total}")
    print(f"  Critic 否决: {reject_count} ({reject_rate:.0f}%)")
    print(f"  否决率目标: 15-30%")
    print(f"\n[DONE] 连续 5 日验证完成")


if __name__ == "__main__":
    main()
