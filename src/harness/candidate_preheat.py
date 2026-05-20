"""候选股知识预热协调器。

scan 输出候选池后，对每只股自动拉取近 90 天公告 PDF + 30 天研报，
入库 LanceDB 知识库。失败不阻塞批量。
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

from sandboxes.data import cninfo_client, knowledge_store, tushare_client

log = logging.getLogger(__name__)

_ANN_LIMIT = 30
_REPORT_LIMIT = 10
_INDUSTRY_REPORT_LIMIT = 20
_POLICY_LIMIT = 5
_SINGLE_STOCK_TIMEOUT_SEC = 300  # 5 min
_HIGH_PRIORITY_TYPES = {"业绩预告", "业绩快报", "财报", "重大投资", "对外投资", "资产重组", "股权变动"}


def _ann_type(ann: dict) -> str:
    return ann.get("ann_type") or ann.get("category", "")


def _select_announcements(announcements: list[dict], max_count: int = _ANN_LIMIT) -> list[dict]:
    """优先级排序：重大类型 > 时间倒序。"""
    high = [a for a in announcements if _ann_type(a) in _HIGH_PRIORITY_TYPES]
    low = [a for a in announcements if _ann_type(a) not in _HIGH_PRIORITY_TYPES]
    high.sort(key=lambda x: x.get("ann_date", ""), reverse=True)
    low.sort(key=lambda x: x.get("ann_date", ""), reverse=True)
    return (high + low)[:max_count]


def _code6(ts_code: str) -> str:
    return ts_code.split(".")[0].strip()


def _preheat_one_stock(ts_code: str, stock_name: str, log_fh=None) -> dict:
    """单只股入库。返回统计 dict 或 raise 异常。"""
    t0 = time.time()
    end = datetime.now().strftime("%Y%m%d")
    start_90 = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
    start_30 = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

    ann_count = report_count = industry_report_count = policy_count = 0

    try:
        result = cninfo_client.query_announcements(
            stock=_code6(ts_code), start_date=start_90, end_date=end,
        )
        announcements = result.get("data") or [] if isinstance(result, dict) else []
        selected = _select_announcements(announcements, _ANN_LIMIT)
        for ann in selected:
            try:
                pdf_url = ann.get("pdf_url") or ann.get("url") or ""
                if not pdf_url:
                    continue
                content = cninfo_client.fetch_announcement_text(pdf_url)
                if content:
                    knowledge_store.ingest_announcement(
                        ts_code=ts_code,
                        title=ann.get("title", ""),
                        text=content,
                        ann_date=ann.get("ann_date", ""),
                    )
                    ann_count += 1
            except Exception as e:
                log.warning("[%s] 公告入库失败 %s: %s", ts_code, ann.get("title", "")[:30], e)
    except Exception as e:
        log.warning("[%s] 公告查询失败: %s", ts_code, e)

    try:
        reports_result = tushare_client.get_research_report_by_stock(
            ts_code=ts_code, start_date=start_30, end_date=end,
        )
        reports = (reports_result.get("data") or []) if isinstance(reports_result, dict) else []
        for r in reports[:_REPORT_LIMIT]:
            try:
                full_text = r.get("abstr") or r.get("abstract") or ""
                if full_text:
                    knowledge_store.ingest_report(
                        ts_code=ts_code,
                        title=r.get("title", ""),
                        abstract=full_text,
                        ann_date=r.get("trade_date", r.get("report_date", "")),
                    )
                    report_count += 1
            except Exception:
                pass
    except Exception as e:
        log.warning("[%s] 研报查询失败: %s", ts_code, e)

    elapsed = time.time() - t0
    if log_fh:
        log_fh.write(
            f"[{datetime.now():%H:%M:%S}] {ts_code} {stock_name}: "
            f"ann={ann_count} report={report_count} industry={industry_report_count} "
            f"elapsed={elapsed:.1f}s\n"
        )
        log_fh.flush()

    return {
        "ts_code": ts_code,
        "announcement_count": ann_count,
        "report_count": report_count,
        "industry_report_count": industry_report_count,
        "policy_count": policy_count,
        "elapsed_sec": round(elapsed, 1),
    }


def preheat_candidates(candidate_list: list[dict], output_dir: str = "data/") -> dict:
    """批量预热。失败单股不阻塞批量。"""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / f"preheat_{datetime.now().strftime('%Y%m%d')}.log"
    preheated = []
    failed = []

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n=== preheat batch start {datetime.now()} ===\n")
        for c in candidate_list:
            ts = c["ts_code"]
            name = c.get("stock_name", "")
            try:
                t0 = time.time()
                result = _preheat_one_stock(ts, name, log_fh=f)
                if time.time() - t0 > _SINGLE_STOCK_TIMEOUT_SEC:
                    log.warning("[%s] 超时 (%ss) 但仍完成", ts, _SINGLE_STOCK_TIMEOUT_SEC)
                preheated.append(result)
            except Exception as e:
                log.exception("[%s] preheat 失败", ts)
                failed.append({"ts_code": ts, "error": str(e)})
                f.write(f"[ERROR] {ts}: {e}\n")
        f.write(f"=== preheat batch done {datetime.now()} | ok={len(preheated)} fail={len(failed)} ===\n")

    return {"preheated": preheated, "failed": failed, "log_path": str(log_path)}
