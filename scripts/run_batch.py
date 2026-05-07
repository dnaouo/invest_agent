"""批量分析多只股票。

用法:
    # 直接在命令行指定股票（代码:名称）
    python scripts/run_batch.py 000988.SZ:华工科技 002475.SZ:立讯精密 300750.SZ:宁德时代

    # 从文件读取（每行一个 代码:名称）
    python scripts/run_batch.py --file stocks.txt

    # 指定交易日期（默认 20260430）
    python scripts/run_batch.py --date 20260425 000988.SZ:华工科技

    # 开启 thinking 模式（默认关闭以加速，单只约 6 分钟 vs 开启后可能超时）
    python scripts/run_batch.py --thinking 000988.SZ:华工科技
"""
import argparse
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def parse_stock(s: str) -> tuple[str, str]:
    """解析 '000988.SZ:华工科技' 或 '000988.SZ' 格式。"""
    if ":" in s:
        code, name = s.split(":", 1)
    elif "：" in s:
        code, name = s.split("：", 1)
    else:
        code, name = s.strip(), s.strip()
    return code.strip(), name.strip()


AGENT_KEYS = [
    ("macro_themes", "宏观主题"),
    ("fundamental_score", "基本面"),
    ("technical_score", "技术面"),
    ("event_analysis", "事件驱动"),
    ("flow_institutional", "机构资金"),
    ("flow_hot_money", "游资跟踪"),
    ("risk_assessment", "风险评估"),
    ("backtest_result", "回测验证"),
    ("critic_review", "Critic审查"),
    ("supervisor_signal", "Supervisor信号"),
]


def _print_detail(result: dict, elapsed: float):
    """打印单只股票全部 10 个 agent 的详细结果。"""
    print(f"\n  {'─'*56}")
    for key, label in AGENT_KEYS:
        agent_out = result.get(key, {})
        if not agent_out:
            print(f"  {label:<12} (无数据)")
            continue
        score = agent_out.get("score", "-")
        summary = agent_out.get("summary", "")
        if not summary:
            for fallback in ("direction", "verdict", "worst_case"):
                if fallback in agent_out:
                    summary = f"{fallback}={agent_out[fallback]}"
                    break
        summary_short = summary
        highlights = agent_out.get("highlights", agent_out.get("reasons", []))
        risks = agent_out.get("risks", agent_out.get("objections", []))
        print(f"  {label:<12} 评分:{score:<6} {summary_short}")
        if highlights:
            for h in highlights[:3]:
                print(f"    + {h}")
        if risks:
            for r in risks[:3]:
                print(f"    - {r}")
    print(f"  {'─'*56}")
    print(f"  耗时: {elapsed:.1f}s")


def _save_incremental(path: Path, trade_date: str, stock_list, summary_rows, all_results, elapsed):
    """每只股票完成后增量保存 JSON。"""
    output = {
        "trade_date": trade_date,
        "total_stocks": len(stock_list),
        "completed": len(summary_rows),
        "total_elapsed": round(elapsed, 1),
        "summary": summary_rows,
        "details": {k: v for k, v in all_results.items()},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(description="批量分析多只股票")
    parser.add_argument("stocks", nargs="*", help="股票列表，格式: 代码:名称")
    parser.add_argument("--file", "-f", help="从文件读取股票列表（每行一个 代码:名称）")
    parser.add_argument("--date", "-d", default="20260430", help="交易日期 (默认 20260430)")
    parser.add_argument("--thinking", action="store_true", help="开启 thinking 模式（更慢但可能更准）")
    parser.add_argument("--output", "-o", default="data/batch_result.json", help="输出文件路径")
    args = parser.parse_args()

    stock_list: list[tuple[str, str]] = []

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    stock_list.append(parse_stock(line))

    for s in args.stocks:
        stock_list.append(parse_stock(s))

    if not stock_list:
        parser.error("请指定至少一只股票。示例: python scripts/run_batch.py 000988.SZ:华工科技")

    if not args.thinking:
        import llm_clients.tier_router as tr
        tr.AGENT_TIER_MAP = {k: "B_recall" for k in tr.AGENT_TIER_MAP}
        print("[INFO] thinking=False 加速模式\n")

    from harness.orchestrator import run_analysis

    print(f"批量分析 {len(stock_list)} 只股票，截至 {args.date}")
    print(f"{'='*60}")
    for ts_code, name in stock_list:
        print(f"  {ts_code} {name}")
    print(f"{'='*60}\n")
    sys.stdout.flush()

    all_results = {}
    summary_rows = []
    total_t0 = time.time()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    for i, (ts_code, stock_name) in enumerate(stock_list, 1):
        if i > 1:
            print(f"  [冷却 10s 避免限流...]")
            sys.stdout.flush()
            time.sleep(10)
        print(f"\n{'='*60}")
        print(f"[{i}/{len(stock_list)}] {stock_name}（{ts_code}）")
        print(f"{'='*60}")
        sys.stdout.flush()

        t0 = time.time()
        try:
            result = run_analysis(ts_code, args.date, stock_name)
            elapsed = time.time() - t0

            fund = result.get("fundamental_score", {})
            tech = result.get("technical_score", {})
            event = result.get("event_analysis", {})
            critic = result.get("critic_review", {})
            signal = result.get("supervisor_signal", {})

            row = {
                "ts_code": ts_code,
                "stock_name": stock_name,
                "fund_score": fund.get("score", "N/A"),
                "tech_score": tech.get("score", "N/A"),
                "event_score": event.get("score", "N/A"),
                "critic_score": critic.get("score", "N/A"),
                "critic_verdict": critic.get("verdict", "N/A"),
                "direction": signal.get("direction", "N/A"),
                "confidence": signal.get("confidence", "N/A"),
                "position_pct": signal.get("position_pct", "N/A"),
                "elapsed": round(elapsed, 1),
                "status": "ok",
            }
            summary_rows.append(row)
            all_results[ts_code] = result

            _print_detail(result, elapsed)

        except Exception as e:
            elapsed = time.time() - t0
            print(f"  失败 ({elapsed:.1f}s): {e}")
            traceback.print_exc()
            summary_rows.append({
                "ts_code": ts_code,
                "stock_name": stock_name,
                "status": "error",
                "error": str(e),
                "elapsed": round(elapsed, 1),
            })

        # 增量保存——每只股票完成后立即写入
        _save_incremental(output_path, args.date, stock_list, summary_rows, all_results, time.time() - total_t0)
        sys.stdout.flush()

    total_elapsed = time.time() - total_t0

    # 打印汇总表
    print(f"\n{'='*60}")
    print(f"批量分析完成 — {len(stock_list)} 只股票，总耗时 {total_elapsed:.0f}s")
    print(f"{'='*60}")
    print(f"\n{'股票':<12} {'基本面':>5} {'技术面':>5} {'事件':>5} {'Critic':>7} {'信号':<6} {'置信度':>5} {'仓位':>5} {'耗时':>6}")
    print("-" * 70)
    for r in summary_rows:
        if r["status"] == "ok":
            print(f"{r['stock_name']:<10} {r['fund_score']:>5} {r['tech_score']:>5} {r['event_score']:>5} "
                  f"{r['critic_score']:>4}/{r['critic_verdict']:<4} {r['direction']:<6} {r['confidence']:>5} {r['position_pct']:>4}% {r['elapsed']:>5.0f}s")
        else:
            print(f"{r['stock_name']:<10} {'ERROR':>5} {'':<38} {r['elapsed']:>5.0f}s")

    # 最终保存
    _save_incremental(output_path, args.date, stock_list, summary_rows, all_results, total_elapsed)
    print(f"\n结果已保存: {output_path}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
