"""研报库：拉取、查询、评级变动检测。"""

from __future__ import annotations

from datetime import datetime, timedelta

from sandboxes.data import tushare_client
from sandboxes.data.duckdb_store import upsert, query

_TABLE = "research_report"


def refresh_reports(report_date: str, db_path: str | None = None) -> int:
    """拉取某日研报摘要入库。upsert 到 research_report 表。返回写入行数。"""
    result = tushare_client.get_research_report(report_date)
    if result["status"] != "ok":
        return 0
    records = result["data"]
    if not records:
        return 0
    return upsert(_TABLE, records, ["title", "report_date"], db_path=db_path)


def get_recent_reports(
    ts_code: str,
    days: int = 30,
    db_path: str | None = None,
) -> list[dict]:
    """获取某标的最近 N 天的研报。

    tushare research_report 不返回 ts_code 字段，通过 title / abstr 模糊匹配。
    ts_code 格式如 '000001.SZ'，取前面的纯数字部分或直接传入股票简称均可匹配。
    """
    end = datetime.now()
    start = end - timedelta(days=days)
    start_str = start.strftime("%Y%m%d")
    end_str = end.strftime("%Y%m%d")

    keyword = ts_code.split(".")[0] if "." in ts_code else ts_code

    sql = (
        f"SELECT * FROM {_TABLE} "
        f"WHERE report_date >= '{start_str}' AND report_date <= '{end_str}' "
        f"AND (title LIKE '%{keyword}%' OR abstr LIKE '%{keyword}%') "
        f"ORDER BY report_date DESC"
    )
    return query(sql, db_path=db_path)


def detect_rating_change(
    ts_code: str,
    days: int = 7,
    db_path: str | None = None,
) -> dict:
    """检测某标的近 N 天是否有多家券商集体上调评级的信号。

    返回 {"signal": True/False, "count": int, "institutions": list[str]}
    简化逻辑：统计 report_type 包含"上调"或"买入"且标题含股票关键词的研报数量，
    >=3 家不同券商算有信号。
    """
    end = datetime.now()
    start = end - timedelta(days=days)
    start_str = start.strftime("%Y%m%d")
    end_str = end.strftime("%Y%m%d")

    keyword = ts_code.split(".")[0] if "." in ts_code else ts_code

    sql = (
        f"SELECT DISTINCT inst_csname FROM {_TABLE} "
        f"WHERE report_date >= '{start_str}' AND report_date <= '{end_str}' "
        f"AND (title LIKE '%{keyword}%' OR abstr LIKE '%{keyword}%') "
        f"AND (report_type LIKE '%上调%' OR report_type LIKE '%买入%') "
    )
    rows = query(sql, db_path=db_path)
    institutions = [r["inst_csname"] for r in rows if r.get("inst_csname")]
    count = len(institutions)
    return {
        "signal": count >= 3,
        "count": count,
        "institutions": institutions,
    }
