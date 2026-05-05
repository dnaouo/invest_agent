"""模拟盘记账 — SQLite 持久化交易记录和组合状态。"""
from __future__ import annotations
import sqlite3
import uuid
from typing import Literal
from pathlib import Path
from pydantic import BaseModel, Field

_DEFAULT_DB = "data/paper_trading.sqlite"


class PaperTrade(BaseModel):
    trade_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: str
    ts_code: str
    direction: Literal["buy", "sell"]
    price: float
    quantity: int
    position_pct: float = 0.0
    signal_confidence: float = 0.0
    critic_score: float = 0.0


class PaperPortfolio(BaseModel):
    date: str
    cash: float = 1_000_000.0
    positions: list[dict] = Field(default_factory=list)
    total_value: float = 1_000_000.0
    daily_return_pct: float = 0.0
    cumulative_return_pct: float = 0.0


def _get_conn(db_path: str | None = None) -> sqlite3.Connection:
    db = db_path or _DEFAULT_DB
    if db != ":memory:":
        Path(db).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS trades (
        trade_id TEXT PRIMARY KEY, date TEXT, ts_code TEXT, direction TEXT,
        price REAL, quantity INTEGER, position_pct REAL,
        signal_confidence REAL, critic_score REAL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS portfolios (
        date TEXT PRIMARY KEY, cash REAL, positions TEXT,
        total_value REAL, daily_return_pct REAL, cumulative_return_pct REAL
    )""")
    conn.commit()


def execute_signal(
    signal: dict,
    portfolio: PaperPortfolio,
    date: str,
    db_path: str | None = None,
) -> PaperTrade | None:
    """根据 supervisor 信号执行模拟交易。direction=hold 时不交易返回 None。"""
    direction = signal.get("direction", "hold")
    if direction == "hold":
        return None
    price = signal.get("stop_loss", 0) or 10.0
    position_pct = signal.get("position_pct", 0)
    if position_pct <= 0:
        return None
    amount = portfolio.total_value * position_pct / 100
    quantity = int(amount / price) if price > 0 else 0
    if quantity <= 0:
        return None
    trade = PaperTrade(
        date=date,
        ts_code=signal.get("ts_code", ""),
        direction=direction,
        price=price,
        quantity=quantity,
        position_pct=position_pct,
        signal_confidence=signal.get("confidence", 0),
        critic_score=signal.get("critic_score", 0),
    )
    conn = _get_conn(db_path)
    conn.execute(
        "INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?)",
        (
            trade.trade_id, trade.date, trade.ts_code, trade.direction,
            trade.price, trade.quantity, trade.position_pct,
            trade.signal_confidence, trade.critic_score,
        ),
    )
    conn.commit()
    conn.close()
    return trade


def update_portfolio(
    portfolio: PaperPortfolio,
    trades: list[PaperTrade],
    date: str,
    db_path: str | None = None,
) -> PaperPortfolio:
    """用当日交易更新组合状态。简化版：只更新 cash 和 positions。"""
    import json

    cash = portfolio.cash
    positions = list(portfolio.positions)
    for t in trades:
        if t.direction == "buy":
            cost = t.price * t.quantity
            cash -= cost
            positions.append({
                "ts_code": t.ts_code, "quantity": t.quantity,
                "entry_price": t.price, "current_price": t.price, "pnl_pct": 0.0,
            })
        elif t.direction == "sell":
            proceeds = t.price * t.quantity
            cash += proceeds
            positions = [p for p in positions if p.get("ts_code") != t.ts_code]
    total_value = cash + sum(
        p.get("current_price", 0) * p.get("quantity", 0) for p in positions
    )
    prev_value = portfolio.total_value or 1_000_000
    daily_return = (total_value - prev_value) / prev_value * 100
    initial = 1_000_000
    cumulative = (total_value - initial) / initial * 100
    new_portfolio = PaperPortfolio(
        date=date, cash=cash, positions=positions,
        total_value=total_value,
        daily_return_pct=round(daily_return, 4),
        cumulative_return_pct=round(cumulative, 4),
    )
    conn = _get_conn(db_path)
    conn.execute(
        "INSERT OR REPLACE INTO portfolios VALUES (?,?,?,?,?,?)",
        (
            date, cash, json.dumps(positions, ensure_ascii=False),
            total_value, new_portfolio.daily_return_pct,
            new_portfolio.cumulative_return_pct,
        ),
    )
    conn.commit()
    conn.close()
    return new_portfolio


def get_portfolio(date: str, db_path: str | None = None) -> PaperPortfolio | None:
    import json

    conn = _get_conn(db_path)
    row = conn.execute(
        "SELECT * FROM portfolios WHERE date = ?", (date,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return PaperPortfolio(
        date=row["date"], cash=row["cash"],
        positions=json.loads(row["positions"]) if row["positions"] else [],
        total_value=row["total_value"],
        daily_return_pct=row["daily_return_pct"],
        cumulative_return_pct=row["cumulative_return_pct"],
    )


def get_trade_history(
    start_date: str, end_date: str, db_path: str | None = None,
) -> list[PaperTrade]:
    conn = _get_conn(db_path)
    rows = conn.execute(
        "SELECT * FROM trades WHERE date >= ? AND date <= ? ORDER BY date",
        (start_date, end_date),
    ).fetchall()
    conn.close()
    return [PaperTrade(**dict(r)) for r in rows]
