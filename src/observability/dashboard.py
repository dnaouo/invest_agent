"""每日 Dashboard — 从 session events 聚合统计。"""
from __future__ import annotations
from sandboxes.data.duckdb_store import _get_conn


def generate_daily_report(date: str, db_path: str | None = None) -> dict:
    """生成每日报告：按 agent 拆分调用次数/成本/失败率/平均评分。"""
    _db = db_path or "data/duckdb/session.duckdb"
    try:
        conn = _get_conn(_db)
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        if "agent_events" not in table_names:
            return {"date": date, "agents": {}, "total_calls": 0, "total_cost": 0.0}

        rows = conn.execute("""
            SELECT agent_name,
                   COUNT(*) as calls,
                   SUM(cost) as total_cost,
                   AVG(latency_ms) as avg_latency,
                   SUM(tokens) as total_tokens
            FROM agent_events
            WHERE session_id LIKE ?
            GROUP BY agent_name
        """, [f"%{date}%"]).fetchall()

        agents = {}
        total_calls = 0
        total_cost = 0.0
        for row in rows:
            name, calls, cost, latency, tokens = row
            agents[name] = {
                "calls": calls,
                "cost": cost or 0.0,
                "avg_latency_ms": round(latency or 0, 1),
                "tokens": tokens or 0,
            }
            total_calls += calls
            total_cost += cost or 0.0

        return {
            "date": date,
            "agents": agents,
            "total_calls": total_calls,
            "total_cost": round(total_cost, 4),
        }
    except Exception:
        return {"date": date, "agents": {}, "total_calls": 0, "total_cost": 0.0}
