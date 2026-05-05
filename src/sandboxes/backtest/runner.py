"""回测 sandbox — 简化版 walk-forward 验证。"""
from __future__ import annotations

from pydantic import BaseModel, Field

from sandboxes.data import tushare_client


class BacktestResult(BaseModel):
    ts_code: str
    start_date: str
    end_date: str
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    calmar: float = 0.0
    total_trades: int = 0
    total_return_pct: float = 0.0


def run_simple_backtest(
    ts_code: str, start_date: str, end_date: str, signal_direction: str = "buy",
) -> BacktestResult:
    """简化版回测：拉取日线数据计算基本统计。"""
    daily = tushare_client.get_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    if daily["status"] != "ok" or not daily["data"]:
        return BacktestResult(ts_code=ts_code, start_date=start_date, end_date=end_date)

    records = sorted(daily["data"], key=lambda x: x.get("trade_date", ""))
    closes = [r["close"] for r in records if "close" in r]
    if len(closes) < 2:
        return BacktestResult(ts_code=ts_code, start_date=start_date, end_date=end_date)

    returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]
    if signal_direction == "sell":
        returns = [-r for r in returns]

    avg_ret = sum(returns) / len(returns)
    std_ret = (sum((r - avg_ret) ** 2 for r in returns) / len(returns)) ** 0.5 if returns else 1
    sharpe = (avg_ret / std_ret * (252 ** 0.5)) if std_ret > 0 else 0

    total_return = (closes[-1] - closes[0]) / closes[0] * 100
    if signal_direction == "sell":
        total_return = -total_return

    peak = closes[0]
    max_dd = 0.0
    for c in closes:
        if c > peak:
            peak = c
        dd = (peak - c) / peak
        if dd > max_dd:
            max_dd = dd

    win_rate = sum(1 for r in returns if r > 0) / len(returns) if returns else 0
    calmar = (total_return / 100) / max_dd if max_dd > 0 else 0

    return BacktestResult(
        ts_code=ts_code, start_date=start_date, end_date=end_date,
        sharpe=round(sharpe, 2), max_drawdown=round(max_dd * 100, 2),
        win_rate=round(win_rate, 2), calmar=round(calmar, 2),
        total_trades=1, total_return_pct=round(total_return, 2),
    )
