"""盘后全市场数据预拉取 + 入库 DuckDB。每天 16:30 运行一次。"""
from __future__ import annotations

from datetime import datetime, timedelta

from sandboxes.data import tushare_client, akshare_client
from sandboxes.data.duckdb_store import upsert

_DB = "data/duckdb/market.duckdb"


def _subtract_days(date_str: str, days: int) -> str:
    dt = datetime.strptime(date_str, "%Y%m%d")
    return (dt - timedelta(days=days)).strftime("%Y%m%d")


def run_daily_prep(trade_date: str, db_path: str | None = None) -> dict:
    """盘后预拉取全市场共享数据。返回各表写入行数统计。"""
    db = db_path or _DB
    stats = {}

    # 1. 研报：近 7 天
    all_reports = []
    for offset in range(7):
        date = _subtract_days(trade_date, offset)
        try:
            result = tushare_client.get_research_report(date)
            if result["status"] == "ok" and result["data"]:
                all_reports.extend(result["data"])
        except Exception:
            pass
    if all_reports:
        stats["research_report"] = upsert("research_report", all_reports, ["title", "report_date"], db_path=db)

    # 2. 政策法规：近 30 天
    try:
        start = _subtract_days(trade_date, 30)
        result = tushare_client.get_npr(start_date=start, end_date=trade_date)
        if result["status"] == "ok" and result["data"]:
            stats["policy"] = upsert("policy", result["data"], ["title", "pub_date"], db_path=db)
    except Exception:
        pass

    # 3. 游资名录（全量拉取，月缓存靠 upsert 去重）
    try:
        result = tushare_client.get_hm_list()
        if result["status"] == "ok" and result["data"]:
            stats["hm_list"] = upsert("hm_list", result["data"], ["hm_name"], db_path=db)
    except Exception:
        pass

    # 4. 龙虎榜 + 机构席位
    for name, func, keys in [
        ("top_list", lambda: tushare_client.get_top_list(trade_date=trade_date), ["ts_code", "trade_date", "exalter"]),
        ("top_inst", lambda: tushare_client.get_top_inst(trade_date=trade_date), ["ts_code", "trade_date"]),
    ]:
        try:
            result = func()
            if result["status"] == "ok" and result["data"]:
                stats[name] = upsert(name, result["data"], keys, db_path=db)
        except Exception:
            pass

    # 5. 板块资金流
    for name, func in [
        ("moneyflow_ind_ths", lambda: tushare_client.get_moneyflow_ind_ths(trade_date=trade_date)),
        ("moneyflow_cnt_ths", lambda: tushare_client.get_moneyflow_cnt_ths(trade_date=trade_date)),
    ]:
        try:
            result = func()
            if result["status"] == "ok" and result["data"]:
                stats[name] = upsert(name, result["data"], ["ts_code", "trade_date"], db_path=db)
        except Exception:
            pass

    # 6. 快讯
    for source, func in [("cls", lambda: akshare_client.get_cls_news(count=200)), ("jin10", lambda: akshare_client.get_jin10_news(count=200))]:
        try:
            result = func()
            if result["status"] == "ok" and result["data"]:
                for r in result["data"]:
                    r["source"] = source
                stats[f"news_{source}"] = upsert("news", result["data"], ["source"], db_path=db)
        except Exception:
            pass

    # 7. 涨跌停
    try:
        result = tushare_client.get_limit_list_d(trade_date=trade_date)
        if result["status"] == "ok" and result["data"]:
            stats["limit_list"] = upsert("limit_list", result["data"], ["ts_code", "trade_date"], db_path=db)
    except Exception:
        pass

    # 8. 板块指数
    try:
        result = tushare_client.get_ths_index()
        if result["status"] == "ok" and result["data"]:
            stats["ths_index"] = upsert("ths_index_cache", result["data"], ["ts_code"], db_path=db)
    except Exception:
        pass

    return stats
