"""Phase 1a 端到端验证脚本：华工科技基本面分析 + Critic 评审。"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from harness.orchestrator import run_analysis
from session.notes import write_note


def main():
    parser = argparse.ArgumentParser(description="运行单标的分析")
    parser.add_argument("--ts_code", default="000988.SZ")
    parser.add_argument("--trade_date", default="20260430")
    parser.add_argument("--stock_name", default="华工科技")
    args = parser.parse_args()

    print(f"=== 分析 {args.stock_name}（{args.ts_code}）截至 {args.trade_date} ===\n")

    result = run_analysis(args.ts_code, args.trade_date, args.stock_name)

    fund = result.get("fundamental_score", {})
    print("--- 基本面评分 ---")
    print(f"  Score: {fund.get('score', 'N/A')}")
    print(f"  Highlights: {fund.get('highlights', [])}")
    print(f"  Risks: {fund.get('risks', [])}")
    print(f"  Summary: {fund.get('summary', '')[:200]}")

    critic = result.get("critic_review", {})
    print("\n--- Critic 评审 ---")
    print(f"  Score: {critic.get('score', 'N/A')}")
    print(f"  Verdict: {critic.get('verdict', 'N/A')}")
    print(f"  Objections: {critic.get('objections', [])}")
    print(f"  Worst Case: {critic.get('worst_case', '')}")

    note_content = f"# {args.stock_name}（{args.ts_code}）分析报告\n\n"
    note_content += f"日期：{args.trade_date}\n\n"
    note_content += f"## 基本面\n{json.dumps(fund, ensure_ascii=False, indent=2, default=str)}\n\n"
    note_content += f"## Critic 评审\n{json.dumps(critic, ensure_ascii=False, indent=2, default=str)}\n"

    note_path = write_note(args.trade_date, note_content)
    print(f"\n报告已写入：{note_path}")


if __name__ == "__main__":
    main()
