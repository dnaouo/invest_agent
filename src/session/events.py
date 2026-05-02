"""Agent 事件日志 — append-only DuckDB 表。"""
from __future__ import annotations
import uuid
import time
from sandboxes.data.duckdb_store import _get_conn

_EVENTS_DB_PATH = "data/duckdb/session.duckdb"
_TABLE = "agent_events"
_INITIALIZED: dict[str, bool] = {}


def _ensure_table(db_path: str | None = None) -> None:
    """确保 agent_events 表存在。"""
    db_path = db_path or _EVENTS_DB_PATH
    if db_path in _INITIALIZED:
        return
    conn = _get_conn(db_path)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {_TABLE} (
            event_id VARCHAR PRIMARY KEY,
            ts DOUBLE,
            session_id VARCHAR,
            agent_name VARCHAR,
            event_type VARCHAR,
            input_hash VARCHAR,
            output VARCHAR,
            tokens BIGINT,
            cost DOUBLE,
            model VARCHAR,
            latency_ms DOUBLE
        )
    """)
    _INITIALIZED[db_path] = True


def emit_event(
    session_id: str,
    event_type: str,
    payload: dict,
    db_path: str | None = None,
) -> str:
    """写入一条事件，返回 event_id。
    payload 应包含 agent_name, input_hash, output, tokens, cost, model, latency_ms 等字段（都可选）。
    """
    db_path = db_path or _EVENTS_DB_PATH
    _ensure_table(db_path)
    event_id = str(uuid.uuid4())
    conn = _get_conn(db_path)
    conn.execute(
        f"INSERT INTO {_TABLE} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            event_id,
            time.time(),
            session_id,
            payload.get("agent_name", ""),
            event_type,
            payload.get("input_hash", ""),
            payload.get("output", ""),
            payload.get("tokens", 0),
            payload.get("cost", 0.0),
            payload.get("model", ""),
            payload.get("latency_ms", 0.0),
        ],
    )
    return event_id


def get_events(
    session_id: str,
    event_type: str | None = None,
    limit: int = 100,
    db_path: str | None = None,
) -> list[dict]:
    """读取事件日志。可选按 event_type 过滤。"""
    db_path = db_path or _EVENTS_DB_PATH
    _ensure_table(db_path)
    conn = _get_conn(db_path)
    sql = f"SELECT * FROM {_TABLE} WHERE session_id = ?"
    params: list = [session_id]
    if event_type:
        sql += " AND event_type = ?"
        params.append(event_type)
    sql += f" ORDER BY ts DESC LIMIT {limit}"
    result = conn.execute(sql, params)
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def wake(session_id: str, db_path: str | None = None) -> dict:
    """启动/恢复一个 session。

    1. 查询该 session_id 是否有历史事件
    2. 如果没有（新 session）：emit 一个 'session_start' 事件，返回 {"is_new": True, ...}
    3. 如果有（恢复 session）：返回 {"is_new": False, "event_count": N, ...}
    """
    db_path = db_path or _EVENTS_DB_PATH
    _ensure_table(db_path)
    conn = _get_conn(db_path)

    row = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM {_TABLE} WHERE session_id = ?",
        [session_id],
    ).fetchone()
    count = row[0]

    if count == 0:
        emit_event(session_id, "session_start", {"agent_name": "system"}, db_path=db_path)
        return {"is_new": True, "session_id": session_id, "event_count": 0}

    last = conn.execute(
        f"SELECT event_type, agent_name FROM {_TABLE} "
        f"WHERE session_id = ? ORDER BY ts DESC, rowid DESC LIMIT 1",
        [session_id],
    ).fetchone()
    return {
        "is_new": False,
        "session_id": session_id,
        "event_count": count,
        "last_event_type": last[0],
        "last_agent": last[1],
    }
