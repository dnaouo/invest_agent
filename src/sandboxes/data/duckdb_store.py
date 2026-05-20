import re

import duckdb
from pathlib import Path

_DEFAULT_DB_PATH = "data/duckdb/market.duckdb"

_read_connections: dict[str, duckdb.DuckDBPyConnection] = {}
_write_connections: dict[str, duckdb.DuckDBPyConnection] = {}

# 向后兼容：旧测试/代码用 _connections.clear() 或 _connections.pop(":memory:") 做隔离。
# 让 _connections 成为 _write_connections 的别名，确保旧清理逻辑能正确作用于实际池。
# 只读别名（向后兼容）：禁止外部代码做 `_connections[x] = ...` 赋值，
# 否则会污染 _write_connections 池。仅作 .pop / .clear / 遍历用途
_connections = _write_connections

_PY_TO_DUCKDB = {
    str: "VARCHAR",
    int: "BIGINT",
    float: "DOUBLE",
    bool: "BOOLEAN",
}

_SAFE_IDENTIFIER = re.compile(r"^[\w\u4e00-\u9fff]+$")


def _validate_identifier(name: str) -> None:
    """防止 SQL 注入：只允许字母、数字、下划线、中文字符。"""
    if not _SAFE_IDENTIFIER.match(name):
        raise ValueError(f"Unsafe SQL identifier: {name!r}")


def _quote(name: str) -> str:
    _validate_identifier(name)
    return f'"{name}"'


def _ensure_db_dir(db_path: str) -> None:
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)


def _get_read_conn(db_path: str | None = None) -> duckdb.DuckDBPyConnection:
    """获取 read-only 连接。可多个共存。"""
    db_path = db_path or _DEFAULT_DB_PATH
    if db_path == ":memory:":
        # 内存库不支持 read_only=True，所有访问走写连接（且 close 后数据丢失）
        return _get_write_conn(db_path)
    _ensure_db_dir(db_path)
    if db_path in _read_connections:
        return _read_connections[db_path]
    conn = duckdb.connect(db_path, read_only=True)
    _read_connections[db_path] = conn
    return conn


def _get_write_conn(db_path: str | None = None) -> duckdb.DuckDBPyConnection:
    """获取写连接。使用完应立即 _release_write_conn(db_path) 释放。"""
    db_path = db_path or _DEFAULT_DB_PATH
    _ensure_db_dir(db_path)
    if db_path in _write_connections:
        return _write_connections[db_path]
    # 写连接打开前必须先释放已有的 read_only 连接（DuckDB 不允许同 path 同时存在 read+write）
    if db_path in _read_connections:
        try:
            _read_connections[db_path].close()
        except Exception:
            pass
        del _read_connections[db_path]
    conn = duckdb.connect(db_path)
    _write_connections[db_path] = conn
    return conn


def _release_write_conn(db_path: str | None = None) -> None:
    db_path = db_path or _DEFAULT_DB_PATH
    # :memory: 不要释放，否则数据丢失（每次 connect 产生独立库的反面：close 即销毁）
    if db_path == ":memory:":
        return
    conn = _write_connections.pop(db_path, None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass


def _get_conn(db_path: str | None = None) -> duckdb.DuckDBPyConnection:
    """向后兼容：等同于 _get_write_conn，保留旧接口。"""
    return _get_write_conn(db_path)


def _infer_columns(records: list[dict]) -> list[tuple[str, str]]:
    cols: list[tuple[str, str]] = []
    seen: set[str] = set()
    for record in records:
        for key in record:
            if key not in seen:
                seen.add(key)
                cols.append((key, "VARCHAR"))

    inferred: dict[str, str] = {}
    mixed: set[str] = set()
    for record in records:
        for key, value in record.items():
            if value is None:
                continue
            duckdb_type = _PY_TO_DUCKDB.get(type(value), "VARCHAR")
            if key not in inferred:
                inferred[key] = duckdb_type
            elif inferred[key] != duckdb_type:
                mixed.add(key)

    return [(key, "VARCHAR" if key in mixed else inferred.get(key, default_type)) for key, default_type in cols]


def _ensure_table(conn: duckdb.DuckDBPyConnection, table_name: str, columns: list[tuple[str, str]]) -> None:
    qt = _quote(table_name)
    col_defs = ", ".join(f'{_quote(c)} {t}' for c, t in columns)
    conn.execute(f"CREATE TABLE IF NOT EXISTS {qt} ({col_defs})")

    # Schema migration: 添加新列（已有表可能缺少新写入数据中的列）
    try:
        existing = {desc[0] for desc in conn.execute(f"DESCRIBE {qt}").fetchall()}
    except Exception:
        return
    for col_name, col_type in columns:
        if col_name not in existing:
            conn.execute(f"ALTER TABLE {qt} ADD COLUMN {_quote(col_name)} {col_type}")


def upsert(
    table_name: str,
    records: list[dict],
    key_columns: list[str],
    db_path: str | None = None,
) -> int:
    if not records:
        return 0

    _validate_identifier(table_name)
    for k in key_columns:
        _validate_identifier(k)

    conn = _get_write_conn(db_path)

    try:
        columns = _infer_columns(records)
        column_types = dict(columns)
        clean_records = []
        for rec in records:
            clean_records.append({
                k: (str(v) if v is not None and column_types[k] == "VARCHAR" else v)
                for k, v in rec.items()
            })
        _ensure_table(conn, table_name, columns)

        col_names = [c for c, _ in columns]
        tmp = f"_tmp_{table_name}"
        _validate_identifier(tmp)

        col_defs = ", ".join(f'{_quote(c)} {t}' for c, t in columns)
        placeholders = ", ".join("?" for _ in col_names)
        quoted_cols = ", ".join(_quote(c) for c in col_names)

        qt = _quote(table_name)
        qtmp = _quote(tmp)

        conn.execute("BEGIN TRANSACTION")
        try:
            conn.execute(f"CREATE TEMP TABLE {qtmp} ({col_defs})")

            insert_sql = f"INSERT INTO {qtmp} ({quoted_cols}) VALUES ({placeholders})"
            for rec in clean_records:
                values = [rec.get(c) for c in col_names]
                conn.execute(insert_sql, values)

            key_match = " AND ".join(f'{qt}.{_quote(k)} = {qtmp}.{_quote(k)}' for k in key_columns)
            conn.execute(f"DELETE FROM {qt} WHERE EXISTS (SELECT 1 FROM {qtmp} WHERE {key_match})")
            conn.execute(f"INSERT INTO {qt} ({quoted_cols}) SELECT {quoted_cols} FROM {qtmp}")
            conn.execute(f"DROP TABLE {qtmp}")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

        return len(records)
    finally:
        _release_write_conn(db_path)


def query(sql: str, db_path: str | None = None) -> list[dict]:
    conn = _get_read_conn(db_path)
    upper = sql.strip().upper()
    if any(upper.startswith(kw) for kw in ("DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE")):
        raise ValueError("query() only accepts read-only SQL (SELECT / SHOW / DESCRIBE)")
    result = conn.execute(sql)
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def query_safe(sql: str, params: list | None = None, db_path: str | None = None) -> list[dict]:
    """参数化查询，防止 SQL 注入。

    用法：query_safe("SELECT * FROM t WHERE col = $1 AND name LIKE $2", [value, f"%{keyword}%"], db_path)
    DuckDB 使用 $1, $2 ... 作为占位符。
    """
    conn = _get_read_conn(db_path)
    upper = sql.strip().upper()
    if any(upper.startswith(kw) for kw in ("DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE")):
        raise ValueError("query_safe() only accepts read-only SQL (SELECT / SHOW / DESCRIBE)")
    if params:
        result = conn.execute(sql, params)
    else:
        result = conn.execute(sql)
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def close(db_path: str | None = None) -> None:
    db_path = db_path or _DEFAULT_DB_PATH
    for pool in (_read_connections, _write_connections, _connections):
        conn = pool.pop(db_path, None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
