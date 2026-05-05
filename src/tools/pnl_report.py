"""PnL 统计与基准对比。"""
from __future__ import annotations

from sandboxes.data import tushare_client  # noqa: F401


def compute_pnl(portfolio_history: list[dict]) -> dict:
    """从 portfolio 历史计算 PnL 统计。
    portfolio_history: [{date, total_value, daily_return_pct}, ...]
    """
    if not portfolio_history:
        return {"cumulative_return_pct": 0, "max_drawdown_pct": 0, "sharpe": 0, "win_rate": 0, "trading_days": 0}

    values = [p["total_value"] for p in portfolio_history]
    daily_returns = [p.get("daily_return_pct", 0) for p in portfolio_history]
    initial = values[0] if values else 1_000_000
    final = values[-1] if values else initial

    cumulative = (final - initial) / initial * 100

    peak = values[0]
    max_dd = 0
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    avg_ret = sum(daily_returns) / len(daily_returns) if daily_returns else 0
    std_ret = (sum((r - avg_ret) ** 2 for r in daily_returns) / len(daily_returns)) ** 0.5 if daily_returns else 1
    sharpe = (avg_ret / std_ret * (252 ** 0.5)) if std_ret > 0 else 0

    win_days = sum(1 for r in daily_returns if r > 0)
    win_rate = win_days / len(daily_returns) if daily_returns else 0

    return {
        "cumulative_return_pct": round(cumulative, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe": round(sharpe, 2),
        "win_rate": round(win_rate, 2),
        "trading_days": len(portfolio_history),
    }


def compare_benchmark(portfolio_history: list[dict], benchmark_data: list[dict]) -> dict:
    """与基准对比。"""
    pnl = compute_pnl(portfolio_history)
    if not benchmark_data:
        return {**pnl, "benchmark_return_pct": 0, "excess_return_pct": pnl["cumulative_return_pct"]}
    bm_closes = [d.get("close", 0) for d in sorted(benchmark_data, key=lambda x: x.get("trade_date", ""))]
    if len(bm_closes) >= 2 and bm_closes[0] > 0:
        bm_return = (bm_closes[-1] - bm_closes[0]) / bm_closes[0] * 100
    else:
        bm_return = 0
    excess = pnl["cumulative_return_pct"] - bm_return
    return {**pnl, "benchmark_return_pct": round(bm_return, 2), "excess_return_pct": round(excess, 2)}


def generate_pnl_report(portfolio_history: list[dict], benchmark_data: list[dict] | None = None) -> str:
    """生成 markdown 格式 PnL 报告。"""
    stats = compare_benchmark(portfolio_history, benchmark_data or [])
    lines = [
        "# 模拟盘 PnL 报告\n",
        f"- 交易天数：{stats['trading_days']}",
        f"- 累计收益：{stats['cumulative_return_pct']}%",
        f"- 最大回撤：{stats['max_drawdown_pct']}%",
        f"- 夏普比率：{stats['sharpe']}",
        f"- 胜率：{stats['win_rate']:.0%}",
        f"- 基准收益：{stats.get('benchmark_return_pct', 'N/A')}%",
        f"- 超额收益：{stats.get('excess_return_pct', 'N/A')}%",
    ]
    return "\n".join(lines)
