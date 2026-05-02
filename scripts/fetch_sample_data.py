"""Phase 0b 端到端验收脚本：拉取华工科技 000988.SZ 核心数据并入库 DuckDB。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sandboxes.data import tushare_client, akshare_client
from sandboxes.data.duckdb_store import upsert, query, close

TS_CODE = "000988.SZ"
DB_PATH = "data/duckdb/market.duckdb"


def fetch_and_store(label: str, api_func, params: dict, table: str, keys: list[str]) -> int:
    result = api_func(**params)
    if result["status"] != "ok":
        print(f"  [FAIL] {label}: {result.get('message', 'unknown error')}")
        return 0
    count = upsert(table, result["data"], keys, db_path=DB_PATH)
    print(f"  [OK]   {label}: {count} rows")
    return count


def main():
    print("=" * 60)
    print("Phase 0b 验收：华工科技 000988.SZ 数据拉取 + DuckDB 入库")
    print("=" * 60)

    total = 0

    print("\n--- Tushare 接口 ---")

    total += fetch_and_store(
        "日线 (5年)", tushare_client.get_daily,
        {"ts_code": TS_CODE, "start_date": "20210101", "end_date": "20260502"},
        "daily", ["ts_code", "trade_date"],
    )

    total += fetch_and_store(
        "利润表", tushare_client.get_income,
        {"ts_code": TS_CODE, "period": "20241231"},
        "income", ["ts_code", "ann_date", "end_date"],
    )

    total += fetch_and_store(
        "资产负债表", tushare_client.get_balancesheet,
        {"ts_code": TS_CODE, "period": "20241231"},
        "balancesheet", ["ts_code", "ann_date", "end_date"],
    )

    total += fetch_and_store(
        "现金流量表", tushare_client.get_cashflow,
        {"ts_code": TS_CODE, "period": "20241231"},
        "cashflow", ["ts_code", "ann_date", "end_date"],
    )

    total += fetch_and_store(
        "财务指标", tushare_client.get_fina_indicator,
        {"ts_code": TS_CODE, "period": "20241231"},
        "fina_indicator", ["ts_code", "ann_date", "end_date"],
    )

    total += fetch_and_store(
        "业绩预告", tushare_client.get_forecast,
        {"ts_code": TS_CODE},
        "forecast", ["ts_code", "ann_date"],
    )

    total += fetch_and_store(
        "PE/PB/换手率", tushare_client.get_daily_basic,
        {"ts_code": TS_CODE, "start_date": "20260101", "end_date": "20260502"},
        "daily_basic", ["ts_code", "trade_date"],
    )

    total += fetch_and_store(
        "解禁明细", tushare_client.get_share_float,
        {"ts_code": TS_CODE},
        "share_float", ["ts_code", "ann_date", "float_date"],
    )

    total += fetch_and_store(
        "大股东增减持", tushare_client.get_stk_holdertrade,
        {"ts_code": TS_CODE, "start_date": "20210101", "end_date": "20260502"},
        "stk_holdertrade", ["ts_code", "ann_date", "holder_name"],
    )

    total += fetch_and_store(
        "沪深港通资金流", tushare_client.get_moneyflow_hsgt,
        {"start_date": "20260401", "end_date": "20260502"},
        "moneyflow_hsgt", ["trade_date"],
    )

    total += fetch_and_store(
        "股权质押", tushare_client.get_pledge_stat,
        {"ts_code": TS_CODE},
        "pledge_stat", ["ts_code", "end_date"],
    )

    print("\n--- AKShare 接口 ---")

    total += fetch_and_store(
        "财联社快讯 (20条)", akshare_client.get_cls_news,
        {"count": 20},
        "cls_news", ["标题", "发布时间"],
    )

    print(f"\n--- 总计入库 {total} 行 ---")

    print("\n--- DuckDB 验证查询 ---")

    rows = query("SELECT COUNT(*) as cnt FROM daily WHERE ts_code = '000988.SZ'", db_path=DB_PATH)
    print(f"  daily 表华工科技行数: {rows[0]['cnt']}")

    rows = query("SELECT MIN(trade_date) as min_dt, MAX(trade_date) as max_dt FROM daily WHERE ts_code = '000988.SZ'", db_path=DB_PATH)
    print(f"  daily 日期范围: {rows[0]['min_dt']} ~ {rows[0]['max_dt']}")

    rows = query("SELECT COUNT(*) as cnt FROM income WHERE ts_code = '000988.SZ'", db_path=DB_PATH)
    print(f"  income 表华工科技行数: {rows[0]['cnt']}")

    tables = query("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'", db_path=DB_PATH)
    print(f"  DuckDB 表列表: {[t['table_name'] for t in tables]}")

    close(db_path=DB_PATH)
    print("\n[DONE] Phase 0b 验收完成")


if __name__ == "__main__":
    main()
