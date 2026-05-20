"""游资席位联表查询：龙虎榜 + 大宗交易 × 游资名录。"""

from __future__ import annotations

from sandboxes.data import tushare_client
from sandboxes.data.duckdb_store import query


def get_today_hot_money(trade_date: str, db_path: str | None = None) -> list[dict]:
    """联表查询：今天哪个游资买了哪只股票多少钱。

    1. 拉取龙虎榜明细 (top_list)
    2. 拉取大宗交易 (block_trade)
    3. 把营业部名称与 hm_list 表做模糊匹配
    4. 返回匹配到的游资交易记录
    """
    matched: list[dict] = []

    top_result = tushare_client.get_top_list(trade_date)
    if top_result["status"] == "ok":
        for rec in top_result["data"]:
            broker = rec.get("exalter") or rec.get("broker_name") or ""
            if not broker:
                continue
            safe = broker.replace("'", "''")
            rows = query(
                f"SELECT * FROM hm_list WHERE hm_name LIKE '%{safe}%' LIMIT 1",
                db_path=db_path,
            )
            if rows:
                matched.append({
                    "source": "top_list",
                    "ts_code": rec.get("ts_code"),
                    "trade_date": rec.get("trade_date"),
                    "broker": broker,
                    "buy": rec.get("buy"),
                    "sell": rec.get("sell"),
                    "net_buy": rec.get("net_buy"),
                    "hm_info": rows[0],
                })

    block_result = tushare_client.get_block_trade(trade_date)
    if block_result["status"] == "ok":
        for rec in block_result["data"]:
            for side_key in ("buyer", "seller"):
                broker = rec.get(side_key) or ""
                if not broker:
                    continue
                safe = broker.replace("'", "''")
                rows = query(
                    f"SELECT * FROM hm_list WHERE hm_name LIKE '%{safe}%' LIMIT 1",
                    db_path=db_path,
                )
                if rows:
                    matched.append({
                        "source": "block_trade",
                        "ts_code": rec.get("ts_code"),
                        "trade_date": rec.get("trade_date"),
                        "broker": broker,
                        "side": side_key,
                        "price": rec.get("price"),
                        "vol": rec.get("vol"),
                        "amount": rec.get("amount"),
                        "hm_info": rows[0],
                    })

    return matched
