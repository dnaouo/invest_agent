"""事件分类标签体系。

从 tushare 数据源（业绩预告、限售解禁、股东增减持）提取事件，
基于关键词匹配进行分类，并入库 DuckDB。
"""

from __future__ import annotations

from enum import Enum

from sandboxes.data import tushare_client
from sandboxes.data.duckdb_store import upsert


class EventType(str, Enum):
    EARNINGS_BEAT = "earnings_beat"
    EARNINGS_MISS = "earnings_miss"
    IPO_UNLOCK = "ipo_unlock"
    HOLDER_INCREASE = "holder_increase"
    HOLDER_DECREASE = "holder_decrease"
    RESTRUCTURE = "restructure"
    BUYBACK = "buyback"
    EQUITY_INCENTIVE = "equity_incentive"


_BEAT_KEYWORDS = ("预增", "略增", "扭亏")
_MISS_KEYWORDS = ("预减", "略减", "首亏", "续亏")

_EVENTS_TABLE = "events"
_EVENTS_KEYS = ["ts_code", "event_type", "ann_date"]


def _classify_forecast(records: list[dict]) -> list[dict]:
    """从业绩预告数据中提取事件。"""
    events: list[dict] = []
    for rec in records:
        forecast_type = rec.get("type", "")
        if not forecast_type:
            continue

        event_type: str | None = None
        if any(kw in forecast_type for kw in _BEAT_KEYWORDS):
            event_type = EventType.EARNINGS_BEAT.value
        elif any(kw in forecast_type for kw in _MISS_KEYWORDS):
            event_type = EventType.EARNINGS_MISS.value

        if event_type is None:
            continue

        summary = rec.get("summary", "")
        detail = f"{forecast_type}: {summary}" if summary else forecast_type

        events.append({
            "ts_code": rec.get("ts_code", ""),
            "event_type": event_type,
            "strength": 0.9,
            "source": "forecast",
            "ann_date": rec.get("ann_date", ""),
            "detail": detail,
        })
    return events


def _classify_share_float(records: list[dict]) -> list[dict]:
    """从解禁数据中提取事件。"""
    events: list[dict] = []
    for rec in records:
        float_date = rec.get("float_date", "") or rec.get("ann_date", "")
        events.append({
            "ts_code": rec.get("ts_code", ""),
            "event_type": EventType.IPO_UNLOCK.value,
            "strength": 0.7,
            "source": "share_float",
            "ann_date": float_date,
            "detail": f"解禁股数: {rec.get('float_share', '')}",
        })
    return events


def _classify_holdertrade(records: list[dict]) -> list[dict]:
    """从大股东增减持数据中提取事件。"""
    events: list[dict] = []
    for rec in records:
        in_de = rec.get("in_de", "")
        trade_type = rec.get("trade_type", "")
        holder_name = rec.get("holder_name", "")

        event_type: str | None = None
        strength = 0.6

        if in_de == "IN" or "增" in trade_type:
            event_type = EventType.HOLDER_INCREASE.value
            strength = 0.6
        elif in_de == "DE" or "减" in trade_type:
            event_type = EventType.HOLDER_DECREASE.value
            strength = 0.8

        if event_type is None:
            continue

        events.append({
            "ts_code": rec.get("ts_code", ""),
            "event_type": event_type,
            "strength": strength,
            "source": "holdertrade",
            "ann_date": rec.get("ann_date", ""),
            "detail": f"{holder_name} {trade_type}",
        })
    return events


def classify_events(
    ts_code: str,
    start_date: str,
    end_date: str,
    db_path: str | None = None,
) -> list[dict]:
    """聚合所有事件源，分类并入库。"""
    all_events: list[dict] = []

    forecast_resp = tushare_client.get_forecast(ts_code)
    if forecast_resp.get("status") == "ok":
        all_events.extend(_classify_forecast(forecast_resp.get("data", [])))

    float_resp = tushare_client.get_share_float(ts_code)
    if float_resp.get("status") == "ok":
        all_events.extend(_classify_share_float(float_resp.get("data", [])))

    holder_resp = tushare_client.get_stk_holdertrade(ts_code, start_date, end_date)
    if holder_resp.get("status") == "ok":
        all_events.extend(_classify_holdertrade(holder_resp.get("data", [])))

    if all_events:
        upsert(_EVENTS_TABLE, all_events, _EVENTS_KEYS, db_path=db_path)

    return all_events
