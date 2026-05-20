import pytest
from sandboxes.data import duckdb_store


@pytest.fixture(autouse=True)
def _clear_pools():
    duckdb_store._read_connections.clear()
    duckdb_store._write_connections.clear()
    if hasattr(duckdb_store, "_connections"):
        duckdb_store._connections.clear()
    yield
    duckdb_store._read_connections.clear()
    duckdb_store._write_connections.clear()


def test_read_conn_is_readonly_and_concurrent(tmp_path):
    """同一 db 的两个 _get_read_conn 调用复用同一连接，且确实是 read-only。"""
    db = str(tmp_path / "t.duckdb")
    duckdb_store.upsert("foo", [{"a": 1, "b": "x"}], ["a"], db_path=db)
    r1 = duckdb_store._get_read_conn(db)
    r2 = duckdb_store._get_read_conn(db)
    assert r1 is r2, "同 path 的 read_conn 应缓存复用"
    with pytest.raises(Exception):
        r1.execute("INSERT INTO foo VALUES (2, 'y')")


def test_write_conn_released_after_upsert(tmp_path):
    """upsert 完写连接立刻 close，不持有锁。"""
    db = str(tmp_path / "t2.duckdb")
    duckdb_store.upsert("bar", [{"a": 1}], ["a"], db_path=db)
    assert db not in duckdb_store._write_connections, "upsert 后 write_conn 必须释放"


def test_query_uses_read_conn_after_write(tmp_path):
    """write 后 query 走 read_conn 仍能看到刚写的数据。"""
    db = str(tmp_path / "t3.duckdb")
    duckdb_store.upsert("baz", [{"a": 1, "b": "v"}], ["a"], db_path=db)
    rows = duckdb_store.query("SELECT * FROM baz", db_path=db)
    assert len(rows) == 1 and rows[0]["b"] == "v"


def test_concurrent_write_read_no_lock(tmp_path):
    """模拟 daily_data_prep 在写 + hypothesis_engine 在读，不冲突。"""
    db = str(tmp_path / "t4.duckdb")
    duckdb_store.upsert("aa", [{"x": 1}], ["x"], db_path=db)
    rows = duckdb_store.query("SELECT * FROM aa", db_path=db)
    duckdb_store.upsert("aa", [{"x": 2}], ["x"], db_path=db)
    rows2 = duckdb_store.query("SELECT * FROM aa", db_path=db)
    assert len(rows) == 1 and len(rows2) == 2


def test_memory_db_uses_write_conn_for_read(tmp_path):
    """`:memory:` 不能 read_only，必须 fallback 到 write_conn 才能查到刚写的数据。"""
    duckdb_store.upsert("mm", [{"k": 1, "v": "x"}], ["k"], db_path=":memory:")
    rows = duckdb_store.query("SELECT * FROM mm", db_path=":memory:")
    assert len(rows) == 1 and rows[0]["v"] == "x"


def test_get_write_conn_closes_existing_read_conn(tmp_path):
    """_get_write_conn 在 open 写连接前必须 close 已有 read_conn，
    否则 DuckDB 不允许同 path 同时存在 read+write 连接。"""
    db = str(tmp_path / "t5.duckdb")
    duckdb_store.upsert("cc", [{"k": 1}], ["k"], db_path=db)
    r1 = duckdb_store._get_read_conn(db)
    assert db in duckdb_store._read_connections, "read_conn 应已缓存"
    # 触发再次写入 → 应 close 并从池中移除 read_conn
    duckdb_store.upsert("cc", [{"k": 2}], ["k"], db_path=db)
    assert db not in duckdb_store._read_connections, "_get_write_conn 应已 evict read_conn"
    with pytest.raises(Exception):
        r1.execute("SELECT 1")
