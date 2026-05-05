"""每日运行调度器 — 收盘后执行完整分析 + 模拟交易流程。"""
from __future__ import annotations
import json
from harness.orchestrator import run_analysis
from harness.handoff import HandoffArtifact, save_handoff, load_handoff
from harness.sprint_contract import generate_contract
from sandboxes.execute.paper_trading import (
    execute_signal, update_portfolio, get_portfolio, PaperPortfolio,
)
from tools.black_swan import check_batch_anomaly
from session.events import emit_event
from session.notes import write_note


def run_daily(
    date: str,
    stock_pool: list[str] | None = None,
    prev_date: str | None = None,
    db_path: str | None = None,
) -> dict:
    """每日运行流程。返回当日汇总。"""
    pool = stock_pool or ["000988.SZ"]

    # 1. 加载前日 handoff
    prev_handoff = load_handoff(prev_date) if prev_date else None
    handoff_summary = json.dumps(prev_handoff.model_dump(), ensure_ascii=False) if prev_handoff else ""

    # 2. 生成 sprint contract（简化：不实际调 LLM，用默认）
    # generate_contract 需要 Kimi API，在测试中 mock

    # 3. 对每只股票跑分析
    signals = []
    for ts_code in pool:
        try:
            result = run_analysis(ts_code, date, ts_code)
            signal = result.get("supervisor_signal", {})
            signal["ts_code"] = ts_code
            signals.append(signal)
        except Exception as e:
            signals.append({"ts_code": ts_code, "direction": "hold", "confidence": 0, "_error": str(e)})

    # 4. 黑天鹅检测
    is_anomaly, anomaly_reason = check_batch_anomaly(signals)
    if is_anomaly:
        for s in signals:
            s["_needs_human_review"] = True
            s["_anomaly_reason"] = anomaly_reason

    # 5. 执行模拟交易
    portfolio = get_portfolio(prev_date, db_path=db_path) if prev_date else None
    if portfolio is None:
        portfolio = PaperPortfolio(date=date)

    trades = []
    for signal in signals:
        if signal.get("_needs_human_review"):
            continue
        trade = execute_signal(signal, portfolio, date, db_path=db_path)
        if trade:
            trades.append(trade)

    # 6. 更新 portfolio
    portfolio = update_portfolio(portfolio, trades, date, db_path=db_path)

    # 7. 保存 handoff
    artifact = HandoffArtifact(
        date=date,
        positions=portfolio.positions,
        pending_signals=[s for s in signals if s.get("direction") != "hold"],
        learnings=[],
        focus_themes=[],
        blacklist_today=[],
    )
    save_handoff(artifact)

    # 8. 写 note
    note = f"# {date} 每日汇总\n\n信号数: {len(signals)}\n交易数: {len(trades)}\n组合价值: {portfolio.total_value:.0f}\n"
    write_note(date, note)

    # 9. emit event
    emit_event(f"daily_{date}", "daily_run", {
        "agent_name": "daily_runner",
        "output": json.dumps({"signals": len(signals), "trades": len(trades)}, ensure_ascii=False),
    })

    return {
        "date": date,
        "signals": signals,
        "trades": [t.model_dump() for t in trades],
        "portfolio": portfolio.model_dump(),
        "is_anomaly": is_anomaly,
        "anomaly_reason": anomaly_reason if is_anomaly else "",
    }
