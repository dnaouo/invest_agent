"""模拟盘运行脚本。"""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from harness.daily_runner import run_daily
from tools.pnl_report import generate_pnl_report
from sandboxes.execute.paper_trading import get_portfolio


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--pool", default="000988.SZ")
    args = parser.parse_args()

    pool = args.pool.split(",")
    # 简化：用固定日期列表（实际应查交易日历）
    dates = [args.start, args.end]

    print(f"=== 模拟盘 {args.start} ~ {args.end} ===")
    print(f"股票池: {pool}\n")

    prev_date = None
    portfolio_history = []

    for date in dates:
        print(f"--- {date} ---")
        result = run_daily(date, stock_pool=pool, prev_date=prev_date)
        print(f"  信号: {len(result['signals'])}, 交易: {len(result['trades'])}")
        print(f"  组合价值: {result['portfolio']['total_value']:.0f}")
        if result["is_anomaly"]:
            print(f"  [警告] 黑天鹅: {result['anomaly_reason']}")
        portfolio_history.append(result["portfolio"])
        prev_date = date

    print(f"\n=== PnL 报告 ===")
    report = generate_pnl_report(portfolio_history)
    print(report)


if __name__ == "__main__":
    main()
