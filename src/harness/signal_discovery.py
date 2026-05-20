"""每日盘后信号发现 pipeline。从研报、板块异动、快讯、业绩、游资五维度主动发现标的。"""
from __future__ import annotations

import time
from datetime import datetime, timedelta

from sandboxes.data.duckdb_store import query_safe
from sandboxes.data import tushare_client
from sandboxes.data.industry_map import find_related_stocks

_DB = "data/duckdb/market.duckdb"

_HOT_KEYWORDS = [
    "CPO", "光模块", "InP", "磷化铟", "算力", "人形机器人",
    "低轨卫星", "国产替代", "芯片", "半导体", "固态电池", "具身智能",
    "AI", "大模型", "液冷", "HBM", "先进封装", "机器人",
]


def _subtract_days(date_str: str, days: int) -> str:
    dt = datetime.strptime(date_str, "%Y%m%d")
    return (dt - timedelta(days=days)).strftime("%Y%m%d")


def _scan_research_upgrades(trade_date: str, db_path: str) -> list[dict]:
    """研报评级变化信号：近7天同一标的被>=3家券商覆盖，或含买入/增持关键词>=3篇。"""
    start = _subtract_days(trade_date, 7)
    signals = []

    try:
        rows = query_safe(
            "SELECT \"ts_code\", \"name\", COUNT(DISTINCT \"inst_csname\") AS broker_count "
            "FROM research_report "
            "WHERE \"trade_date\" >= $1 AND \"trade_date\" <= $2 "
            "GROUP BY \"ts_code\", \"name\" "
            "HAVING broker_count >= 3",
            [start, trade_date],
            db_path=db_path,
        )
        for r in rows:
            ts_code = r.get("ts_code")
            if not ts_code:
                continue
            signals.append({
                "ts_code": ts_code,
                "stock_name": r.get("name", ""),
                "trigger_source": "research_upgrade",
                "trigger_detail": f"{r.get('broker_count', 0)}家券商近7天覆盖",
                "priority": "high" if int(r.get("broker_count", 0)) >= 5 else "medium",
            })
    except Exception:
        pass

    try:
        rows2 = query_safe(
            "SELECT \"ts_code\", \"name\", COUNT(*) AS cnt "
            "FROM research_report "
            "WHERE \"trade_date\" >= $1 AND \"trade_date\" <= $2 "
            "AND (\"title\" LIKE '%买入%' OR \"title\" LIKE '%增持%' OR \"title\" LIKE '%强烈推荐%') "
            "GROUP BY \"ts_code\", \"name\" "
            "HAVING cnt >= 3",
            [start, trade_date],
            db_path=db_path,
        )
        existing_codes = {s["ts_code"] for s in signals}
        for r in rows2:
            ts_code = r.get("ts_code")
            if not ts_code or ts_code in existing_codes:
                continue
            signals.append({
                "ts_code": ts_code,
                "stock_name": r.get("name", ""),
                "trigger_source": "research_upgrade",
                "trigger_detail": f"近7天{r.get('cnt', 0)}篇买入/增持评级研报",
                "priority": "high",
            })
    except Exception:
        pass

    return signals


def _scan_sector_anomaly(trade_date: str, db_path: str) -> list[dict]:
    """板块异动信号：连续3日净流入>5亿或单日>10亿的板块，取龙头。"""
    signals = []

    try:
        rows = query_safe(
            "SELECT \"ts_code\", \"name\", CAST(\"net_amount\" AS DOUBLE) AS net_amt "
            "FROM moneyflow_cnt_ths "
            "WHERE \"trade_date\" = $1 "
            "AND CAST(\"net_amount\" AS DOUBLE) > 100000000 "
            "ORDER BY net_amt DESC LIMIT 10",
            [trade_date],
            db_path=db_path,
        )
        for r in rows:
            sector_code = r.get("ts_code", "")
            sector_name = r.get("name", "")
            net_amt = float(r.get("net_amt", 0))

            members = []
            try:
                result = tushare_client.get_ths_member(ts_code=sector_code)
                time.sleep(1)
                if result["status"] == "ok" and result["data"]:
                    members = result["data"][:3]
            except Exception:
                pass

            if members:
                for m in members:
                    signals.append({
                        "ts_code": m.get("code", ""),
                        "stock_name": m.get("name", ""),
                        "trigger_source": "sector_anomaly",
                        "trigger_detail": f"板块{sector_name}单日净流入{net_amt / 1e8:.1f}亿",
                        "priority": "high" if net_amt > 2e8 else "medium",
                    })
            else:
                signals.append({
                    "ts_code": sector_code,
                    "stock_name": sector_name,
                    "trigger_source": "sector_anomaly",
                    "trigger_detail": f"板块单日净流入{net_amt / 1e8:.1f}亿（未获取成分股）",
                    "priority": "medium",
                })
    except Exception:
        pass

    # 连续3日净流入>5亿
    try:
        start_3d = _subtract_days(trade_date, 3)
        rows2 = query_safe(
            "SELECT \"ts_code\", \"name\", COUNT(*) AS days_cnt, "
            "SUM(CAST(\"net_amount\" AS DOUBLE)) AS total_net "
            "FROM moneyflow_cnt_ths "
            "WHERE \"trade_date\" >= $1 AND \"trade_date\" <= $2 "
            "AND CAST(\"net_amount\" AS DOUBLE) > 50000000 "
            "GROUP BY \"ts_code\", \"name\" "
            "HAVING days_cnt >= 3 "
            "ORDER BY total_net DESC LIMIT 5",
            [start_3d, trade_date],
            db_path=db_path,
        )
        existing_codes = {s["ts_code"] for s in signals}
        for r in rows2:
            sector_code = r.get("ts_code", "")
            if sector_code in existing_codes:
                continue
            sector_name = r.get("name", "")
            total = float(r.get("total_net", 0))

            try:
                result = tushare_client.get_ths_member(ts_code=sector_code)
                time.sleep(1)
                if result["status"] == "ok" and result["data"]:
                    for m in result["data"][:2]:
                        signals.append({
                            "ts_code": m.get("code", ""),
                            "stock_name": m.get("name", ""),
                            "trigger_source": "sector_anomaly",
                            "trigger_detail": f"板块{sector_name}连续3日净流入共{total / 1e8:.1f}亿",
                            "priority": "medium",
                        })
            except Exception:
                signals.append({
                    "ts_code": sector_code,
                    "stock_name": sector_name,
                    "trigger_source": "sector_anomaly",
                    "trigger_detail": f"连续3日净流入共{total / 1e8:.1f}亿",
                    "priority": "medium",
                })
    except Exception:
        pass

    return signals


def _scan_news_cluster(trade_date: str, db_path: str) -> list[dict]:
    """产业快讯聚类信号：近3天高频提及的产业链关键词。"""
    start = _subtract_days(trade_date, 3)
    signals = []

    try:
        rows = query_safe(
            "SELECT \"title\", \"time\", \"source\" FROM news "
            "WHERE \"time\" >= $1 "
            "ORDER BY \"time\" DESC LIMIT 500",
            [start],
            db_path=db_path,
        )
    except Exception:
        rows = []

    if not rows:
        return signals

    keyword_hits: dict[str, list[str]] = {}
    for r in rows:
        title = str(r.get("title", ""))
        for kw in _HOT_KEYWORDS:
            if kw in title:
                keyword_hits.setdefault(kw, []).append(title)

    for kw, titles in keyword_hits.items():
        if len(titles) >= 5:
            sample = titles[:3]
            priority = "medium" if len(titles) < 10 else "high"
            detail = f"关键词'{kw}'近3天出现{len(titles)}次: {'; '.join(t[:30] for t in sample)}"

            # 通过产业链映射找到相关个股
            try:
                related = find_related_stocks(kw, db_path=db_path)
                for stock in related[:5]:
                    signals.append({
                        "ts_code": stock.get("ts_code", ""),
                        "stock_name": stock.get("name", ""),
                        "trigger_source": "news_cluster",
                        "trigger_detail": f"{detail} | 产业链:{stock.get('source_sector', '')} 位置:{stock.get('chain_position', '')}",
                        "priority": priority,
                    })
            except Exception:
                pass

            if not any(s["trigger_source"] == "news_cluster" and kw in s.get("trigger_detail", "") for s in signals):
                signals.append({
                    "ts_code": "",
                    "stock_name": "",
                    "trigger_source": "news_cluster",
                    "trigger_detail": detail,
                    "priority": priority,
                })

    return signals


def _scan_earnings_beat(trade_date: str, db_path: str) -> list[dict]:
    """业绩超预期信号：业绩预告预增且同比>30%。"""
    signals = []

    try:
        result = tushare_client.get_forecast_vip(date=trade_date)
        if result["status"] == "ok" and result["data"]:
            for r in result["data"]:
                ftype = str(r.get("type", ""))
                if "预增" not in ftype:
                    continue
                change_min = r.get("net_profit_min") or r.get("change_min")
                try:
                    pct = float(change_min) if change_min else 0
                except (ValueError, TypeError):
                    pct = 0
                if pct > 30:
                    signals.append({
                        "ts_code": r.get("ts_code", ""),
                        "stock_name": r.get("name", r.get("ts_code", "")),
                        "trigger_source": "earnings_beat",
                        "trigger_detail": f"业绩预增，同比+{pct:.0f}%",
                        "priority": "high" if pct > 100 else "medium",
                    })
    except Exception:
        pass

    return signals


def _scan_hot_money(trade_date: str, db_path: str) -> list[dict]:
    """游资/龙虎榜信号：知名游资净买入>5000万的标的。"""
    signals = []

    try:
        rows = query_safe(
            "SELECT t.\"ts_code\", t.\"exalter\", "
            "CAST(t.\"buy\" AS DOUBLE) AS buy_amt, "
            "CAST(t.\"sell\" AS DOUBLE) AS sell_amt, "
            "h.\"name\" AS hm_name "
            "FROM top_inst t, hm_list h "
            "WHERE t.\"trade_date\" = $1 "
            "AND h.\"orgs\" LIKE '%' || t.\"exalter\" || '%' "
            "AND (CAST(t.\"buy\" AS DOUBLE) - CAST(t.\"sell\" AS DOUBLE)) > 50000000 "
            "ORDER BY (CAST(t.\"buy\" AS DOUBLE) - CAST(t.\"sell\" AS DOUBLE)) DESC "
            "LIMIT 20",
            [trade_date],
            db_path=db_path,
        )
        for r in rows:
            ts_code = r.get("ts_code", "")
            buy = float(r.get("buy_amt", 0) or 0)
            sell = float(r.get("sell_amt", 0) or 0)
            net = buy - sell
            signals.append({
                "ts_code": ts_code,
                "stock_name": "",
                "trigger_source": "hot_money",
                "trigger_detail": f"游资{r.get('hm_name', '')}净买入{net / 1e4:.0f}万",
                "priority": "high" if net > 1e8 else "medium",
            })
    except Exception:
        pass

    return signals


def _scan_major_announcements(trade_date: str, db_path: str) -> list[dict]:
    """扫描当日重大公告，生成信号。

    查 DuckDB announcements 表，找当日有重要公告的股票。
    重大公告判断规则：
    1. 分类为"重大事项"或"资产重组"或"融资公告"
    2. 或标题含关键词：扩产/投资/项目/收购/产能/战略合作/中标/订单/增持/回购/定增 等
    """
    signals: list[dict] = []
    keywords = [
        "扩产", "投资", "项目", "收购", "产能", "战略合作", "中标", "订单",
        "增持", "回购", "定增", "合并", "重组", "配股", "转让",
    ]
    important_categories = {"重大事项", "资产重组", "融资公告"}

    try:
        rows = query_safe(
            'SELECT "ts_code", "title", "category" FROM announcements '
            'WHERE "ann_date" = $1',
            [trade_date],
            db_path=db_path,
        )
    except Exception:
        return signals

    if not rows:
        return signals

    seen_codes: dict[str, dict] = {}
    for row in rows:
        ts_code = row.get("ts_code", "")
        title = row.get("title", "")
        category = row.get("category", "")
        if not ts_code:
            continue

        is_major = False
        matched_keyword = ""
        if category in important_categories:
            is_major = True
            matched_keyword = category
        else:
            for kw in keywords:
                if kw in title:
                    is_major = True
                    matched_keyword = kw
                    break

        if not is_major:
            continue

        if len(ts_code) == 6:
            if ts_code.startswith(("0", "3")):
                ts_code = f"{ts_code}.SZ"
            elif ts_code.startswith("6"):
                ts_code = f"{ts_code}.SH"
            else:
                ts_code = f"{ts_code}.SZ"

        if ts_code in seen_codes:
            existing = seen_codes[ts_code]
            existing["trigger_detail"] += f"; [{matched_keyword}] {title[:60]}"
        else:
            sig = {
                "ts_code": ts_code,
                "stock_name": "",
                "trigger_source": "major_announcement",
                "trigger_detail": f"[{matched_keyword}] {title[:80]}",
                "priority": "high",
            }
            seen_codes[ts_code] = sig

    signals.extend(seen_codes.values())
    return signals


def _get_market_pulse(trade_date: str, db_path: str) -> dict:
    """市场温度：涨跌停家数统计 + 4阶段判断。"""
    limit_up = 0
    limit_down = 0

    try:
        rows = query_safe(
            "SELECT \"limit\" AS lim, COUNT(*) AS cnt "
            "FROM limit_list "
            "WHERE \"trade_date\" = $1 "
            "GROUP BY \"limit\"",
            [trade_date],
            db_path=db_path,
        )
        for r in rows:
            lim = str(r.get("lim", ""))
            cnt = int(r.get("cnt", 0))
            if lim == "U":
                limit_up = cnt
            elif lim == "D":
                limit_down = cnt
    except Exception:
        pass

    if limit_up >= 60:
        phase = "高潮"
    elif limit_up >= 30:
        phase = "发酵"
    elif limit_down > 30:
        phase = "退潮"
    else:
        phase = "冰点"

    return {
        "limit_up_count": limit_up,
        "limit_down_count": limit_down,
        "phase": phase,
    }


def _merge_signals(all_signals: list[dict]) -> list[dict]:
    """合并去重：同一 ts_code 多源触发时保留 priority 最高的，合并 trigger_detail。"""
    priority_rank = {"high": 3, "medium": 2, "low": 1}
    merged: dict[str, dict] = {}

    for sig in all_signals:
        key = sig["ts_code"]
        if not key:
            merged[f"_nocode_{len(merged)}"] = sig
            continue
        if key not in merged:
            merged[key] = dict(sig)
            merged[key]["_sources"] = [sig["trigger_source"]]
        else:
            existing = merged[key]
            existing["_sources"].append(sig["trigger_source"])
            if priority_rank.get(sig["priority"], 0) > priority_rank.get(existing["priority"], 0):
                existing["priority"] = sig["priority"]
            if sig["trigger_source"] != existing["trigger_source"]:
                existing["trigger_detail"] += f" | {sig['trigger_detail']}"
                existing["trigger_source"] = "+".join(sorted(set(existing["_sources"])))
            if not existing["stock_name"] and sig["stock_name"]:
                existing["stock_name"] = sig["stock_name"]

    results = []
    for sig in merged.values():
        sig.pop("_sources", None)
        results.append(sig)

    results.sort(key=lambda x: priority_rank.get(x.get("priority", "low"), 0), reverse=True)
    return results


def discover_signals(trade_date: str, db_path: str | None = None) -> dict:
    """
    每日盘后信号发现。返回值格式：
    {
        "trade_date": "20260402",
        "signals": [...],
        "market_pulse": {...}
    }
    """
    db = db_path or _DB
    all_signals: list[dict] = []

    all_signals.extend(_scan_research_upgrades(trade_date, db))
    all_signals.extend(_scan_sector_anomaly(trade_date, db))
    all_signals.extend(_scan_news_cluster(trade_date, db))
    all_signals.extend(_scan_earnings_beat(trade_date, db))
    all_signals.extend(_scan_hot_money(trade_date, db))
    all_signals.extend(_scan_major_announcements(trade_date, db))

    merged = _merge_signals(all_signals)
    market_pulse = _get_market_pulse(trade_date, db)

    return {
        "trade_date": trade_date,
        "signals": merged,
        "market_pulse": market_pulse,
    }
