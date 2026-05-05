"""防 look-ahead 信息切片工具。"""
from __future__ import annotations


def slice_data(
    data: list[dict], trade_date: str, date_field: str = "trade_date"
) -> list[dict]:
    """按日期截断：只保留 date_field <= trade_date 的记录。
    记录缺少 date_field 时排除（防止意外泄漏未来数据）。
    """
    return [
        r for r in data
        if r.get(date_field) is not None and r[date_field] <= trade_date
    ]


def slice_financial(
    data: list[dict], trade_date: str, ann_date_field: str = "ann_date"
) -> list[dict]:
    """按公告日截断：只保留 ann_date <= trade_date 的记录（防财报穿越）。
    记录缺少 ann_date_field 时排除。
    """
    return [
        r for r in data
        if r.get(ann_date_field) is not None and r[ann_date_field] <= trade_date
    ]
