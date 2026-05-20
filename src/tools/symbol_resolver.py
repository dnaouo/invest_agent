"""ts_code / stock_name 一致性校验工具。

防止「华电辽能」被错误映射到 000609（*ST 中迪）。
基于 tushare stock_basic 全市场名单。DuckDB 缓存（月级 TTL）作为可选预热路径，
validate 本身直接走 _fetch_stock_basic 拿全市场 DataFrame（不强依赖 cache 表）。
"""
from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

from sandboxes.data import tushare_client
from sandboxes.data.duckdb_store import query_safe, upsert

log = logging.getLogger(__name__)

_CACHE_TABLE = "stock_basic_cache"
_CACHE_TTL_DAYS = 30


def _fetch_stock_basic() -> pd.DataFrame:
    """读 tushare stock_basic，转 DataFrame 返回（包装为可 mock 的函数）。"""
    result = tushare_client.get_stock_basic()
    if result.get("status") != "ok":
        return pd.DataFrame()
    return pd.DataFrame(result.get("data", []))


def _ensure_cache(force: bool = False) -> None:
    """每月刷新缓存表。供 daily_data_prep 预热用；validate 不强依赖。"""
    try:
        rows = query_safe(
            f"SELECT max(_fetched_at) AS last FROM {_CACHE_TABLE}",
        )
        last = rows[0]["last"] if rows else None
        if last and not force:
            last_dt = datetime.strptime(str(last)[:10], "%Y-%m-%d")
            if (datetime.now() - last_dt).days < _CACHE_TTL_DAYS:
                return
    except Exception:
        pass
    df = _fetch_stock_basic()
    if df is None or df.empty:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    records = [
        {"ts_code": r["ts_code"], "name": r.get("name", ""), "_fetched_at": today}
        for _, r in df.iterrows()
    ]
    upsert(_CACHE_TABLE, records, key_columns=["ts_code"])


def validate(ts_code: str, expected_name: str = "") -> dict:
    """校验 ts_code 与 expected_name 是否一致。

    Returns:
        {
            "valid": bool,
            "actual_name": str,           # tushare 中该 ts_code 的真实名称
            "suggestions": list[str],     # 当 expected_name 与 actual_name 不匹配时返回模糊推荐
            "error": str
        }
    """
    if not ts_code:
        return {"valid": False, "actual_name": "", "suggestions": [], "error": "ts_code 为空"}

    df = _fetch_stock_basic()
    if df is None or df.empty:
        return {"valid": False, "actual_name": "", "suggestions": [], "error": "stock_basic 查询失败"}

    matched = df[df["ts_code"] == ts_code]
    if matched.empty:
        suggestions: list[str] = []
        if expected_name:
            fuzzy = df[df["name"].str.contains(expected_name, na=False, regex=False)].head(5)
            suggestions = [f"{r['ts_code']} ({r['name']})" for _, r in fuzzy.iterrows()]
        return {
            "valid": False,
            "actual_name": "",
            "suggestions": suggestions,
            "error": f"ts_code {ts_code} 不存在",
        }

    actual = matched.iloc[0]["name"]
    if not expected_name or expected_name == actual:
        return {"valid": True, "actual_name": actual, "suggestions": [], "error": ""}

    fuzzy = df[df["name"].str.contains(expected_name, na=False, regex=False)].head(5)
    suggestions = [f"{r['ts_code']} ({r['name']})" for _, r in fuzzy.iterrows()]
    return {
        "valid": False,
        "actual_name": actual,
        "suggestions": suggestions,
        "error": f"{ts_code} 实际是 {actual}，与 {expected_name} 不符",
    }


def resolve_by_name(name: str, limit: int = 5) -> list[dict]:
    """按名称模糊查找 ts_code。"""
    if not name:
        return []
    df = _fetch_stock_basic()
    if df is None or df.empty:
        return []
    matched = df[df["name"].str.contains(name, na=False, regex=False)].head(limit)
    return [{"ts_code": r["ts_code"], "name": r["name"]} for _, r in matched.iterrows()]


class SymbolMismatchError(ValueError):
    """ts_code 与 stock_name 不一致。"""

    pass
