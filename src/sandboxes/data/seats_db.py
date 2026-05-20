"""游资席位库：名录入库 + 席位查找。"""

from __future__ import annotations

from sandboxes.data import tushare_client
from sandboxes.data.duckdb_store import upsert, query


def refresh_seats(db_path: str | None = None) -> int:
    """拉取 hm_list 全量游资名录，upsert 到 DuckDB hm_list 表。返回写入行数。"""
    result = tushare_client.get_hm_list()
    if result["status"] != "ok":
        raise RuntimeError(f"get_hm_list failed: {result.get('message', 'unknown')}")
    records = result["data"]
    if not records:
        return 0
    return upsert("hm_list", records, ["hm_name"], db_path=db_path)


def lookup_seat(broker_name: str, db_path: str | None = None) -> dict | None:
    """根据营业部名称查找是否是知名游资席位。返回游资信息 dict 或 None。"""
    safe_name = broker_name.replace("'", "''")
    rows = query(
        f"SELECT * FROM hm_list WHERE hm_name LIKE '%{safe_name}%' LIMIT 1",
        db_path=db_path,
    )
    return rows[0] if rows else None
