from sandboxes.data.duckdb_store import upsert, query, close

DB = ":memory:"


def _cleanup():
    close(DB)


def test_upsert_creates_table():
    try:
        records = [
            {"ts_code": "000001.SZ", "trade_date": "20250101", "close": 10.5},
            {"ts_code": "000002.SZ", "trade_date": "20250101", "close": 20.0},
        ]
        n = upsert("daily", records, key_columns=["ts_code", "trade_date"], db_path=DB)
        assert n == 2
        rows = query("SELECT * FROM daily ORDER BY ts_code", db_path=DB)
        assert len(rows) == 2
        assert rows[0]["ts_code"] == "000001.SZ"
        assert rows[1]["close"] == 20.0
    finally:
        _cleanup()


def test_upsert_deduplication():
    try:
        batch1 = [
            {"ts_code": "000001.SZ", "trade_date": "20250101", "close": 10.0},
            {"ts_code": "000002.SZ", "trade_date": "20250101", "close": 20.0},
        ]
        upsert("daily", batch1, key_columns=["ts_code", "trade_date"], db_path=DB)

        batch2 = [
            {"ts_code": "000001.SZ", "trade_date": "20250101", "close": 11.0},
            {"ts_code": "000003.SZ", "trade_date": "20250101", "close": 30.0},
        ]
        upsert("daily", batch2, key_columns=["ts_code", "trade_date"], db_path=DB)

        rows = query("SELECT * FROM daily ORDER BY ts_code", db_path=DB)
        assert len(rows) == 3
        row1 = [r for r in rows if r["ts_code"] == "000001.SZ"][0]
        assert row1["close"] == 11.0
    finally:
        _cleanup()


def test_upsert_empty_records():
    try:
        n = upsert("daily", [], key_columns=["ts_code"], db_path=DB)
        assert n == 0
    finally:
        _cleanup()


def test_query_returns_list_dict():
    try:
        records = [
            {"ts_code": "000001.SZ", "trade_date": "20250101", "close": 10.5},
        ]
        upsert("daily", records, key_columns=["ts_code", "trade_date"], db_path=DB)
        rows = query("SELECT ts_code, close FROM daily", db_path=DB)
        assert isinstance(rows, list)
        assert len(rows) == 1
        assert isinstance(rows[0], dict)
        assert "ts_code" in rows[0]
        assert "close" in rows[0]
    finally:
        _cleanup()
