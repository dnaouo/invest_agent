"""政策法规库：拉取、入库、搜索国家政策法规。"""

from __future__ import annotations

from sandboxes.data import tushare_client
from sandboxes.data.duckdb_store import upsert, query

PTYPE_THEME_MAP: dict[str, list[str]] = {
    "科技": ["半导体", "AI", "信创", "量子计算"],
    "能源": ["光伏", "储能", "新能源车", "氢能"],
    "卫生": ["医药", "医疗器械", "CXO"],
    "教育": ["教育信息化", "职业教育"],
    "金融": ["银行", "保险", "证券"],
    "民航": ["航空", "机场"],
    "农业": ["种业", "农机", "生猪"],
}

_TABLE = "policy"
_KEY_COLUMNS = ["title", "pub_date"]


def refresh_policy(
    org: str = "",
    start_date: str = "",
    end_date: str = "",
    ptype: str = "",
    db_path: str | None = None,
) -> int:
    """拉取政策法规并入库。返回写入行数。"""
    result = tushare_client.get_npr(
        org=org, start_date=start_date, end_date=end_date, ptype=ptype,
    )
    if result["status"] != "ok":
        return 0
    records: list[dict] = result["data"]
    if not records:
        return 0
    return upsert(_TABLE, records, _KEY_COLUMNS, db_path=db_path)


def search_policy(
    keyword: str = "",
    ptype: str = "",
    start_date: str = "",
    end_date: str = "",
    db_path: str | None = None,
) -> list[dict]:
    """搜索政策。keyword 模糊匹配 title 字段。"""
    conditions: list[str] = []
    if keyword:
        safe_kw = keyword.replace("'", "''")
        conditions.append(f"title LIKE '%{safe_kw}%'")
    if ptype:
        safe_pt = ptype.replace("'", "''")
        conditions.append(f"ptype = '{safe_pt}'")
    if start_date:
        conditions.append(f"pub_date >= '{start_date}'")
    if end_date:
        conditions.append(f"pub_date <= '{end_date}'")

    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f'SELECT * FROM "{_TABLE}"{where} ORDER BY pub_date DESC'
    return query(sql, db_path=db_path)


def get_themes_for_ptype(ptype: str) -> list[str]:
    """根据 ptype 返回对应的 A 股主题板块。"""
    return PTYPE_THEME_MAP.get(ptype, [])
