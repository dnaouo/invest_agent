"""新闻聚合器：合并多个源的快讯并入库 DuckDB。"""

from __future__ import annotations

from sandboxes.data import akshare_client
from sandboxes.data.duckdb_store import upsert


_CLS_FIELD_MAP = {
    "标题": "title",
    "内容": "content",
    "发布日期": "date",
    "发布时间": "time",
}

_SINA_FIELD_MAP = {
    "时间": "time",
    "内容": "content",
}


def _normalize_cls(records: list[dict]) -> list[dict]:
    out = []
    for rec in records:
        mapped = {_CLS_FIELD_MAP.get(k, k): str(v) if v is not None else "" for k, v in rec.items()}
        mapped["source"] = "cls"
        if "title" not in mapped:
            mapped["title"] = mapped.get("content", "")[:60]
        out.append(mapped)
    return out


def _normalize_sina(records: list[dict]) -> list[dict]:
    out = []
    for rec in records:
        mapped = {_SINA_FIELD_MAP.get(k, k): str(v) if v is not None else "" for k, v in rec.items()}
        mapped["source"] = "jin10"
        if "title" not in mapped:
            mapped["title"] = mapped.get("content", "")[:60]
        out.append(mapped)
    return out


def fetch_latest_news(count: int = 50, db_path: str | None = None) -> list[dict]:
    """聚合财联社 + 金十（实际为新浪 fallback）两个源的快讯。

    1. 调 akshare_client.get_cls_news(count)
    2. 调 akshare_client.get_jin10_news(count)
    3. 合并两源数据，每条加 "source" 字段
    4. 按 time 降序排列
    5. 去重（title 相同只保留第一条）
    6. 入库 DuckDB "news" 表
    7. 返回合并后的 list[dict]
    """
    all_records: list[dict] = []

    cls_resp = akshare_client.get_cls_news(count)
    if cls_resp.get("status") == "ok":
        all_records.extend(_normalize_cls(cls_resp["data"]))

    jin10_resp = akshare_client.get_jin10_news(count)
    if jin10_resp.get("status") == "ok":
        all_records.extend(_normalize_sina(jin10_resp["data"]))

    all_records.sort(key=lambda r: r.get("time", ""), reverse=True)

    seen_titles: set[str] = set()
    deduped: list[dict] = []
    for rec in all_records:
        t = rec.get("title", "")
        if t and t in seen_titles:
            continue
        seen_titles.add(t)
        deduped.append(rec)

    if deduped and db_path is not None:
        for rec in deduped:
            rec.setdefault("title", "")
            rec.setdefault("content", "")
            rec.setdefault("time", "")
            rec.setdefault("source", "")
            rec.setdefault("date", "")
        upsert("news", deduped, ["title", "source"], db_path=db_path)

    return deduped
