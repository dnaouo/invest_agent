"""巨潮信息网公告查询客户端（免费，无需登录）。"""

import time
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

_BASE_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
_PDF_BASE = "http://static.cninfo.com.cn/"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def query_announcements(stock: str = "", start_date: str = "", end_date: str = "",
                        category: str = "", page_num: int = 1, page_size: int = 30) -> dict:
    """
    查询巨潮公告列表。

    Args:
        stock: 股票代码（如"002428"），空=全市场
        start_date: 开始日期（如"2026-04-01"或"20260401"）
        end_date: 结束日期（如"2026-04-30"或"20260430"）
        category: 公告分类代码，空=全部
        page_num: 页码
        page_size: 每页条数（最大30）

    Returns:
        {"status": "ok", "data": [...], "total_count": N, "has_more": bool}
        每条 data: {"ts_code", "ann_date", "title", "category", "pdf_url"}
    """
    se_date = ""
    if start_date and end_date:
        s = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}" if len(start_date) == 8 else start_date
        e = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}" if len(end_date) == 8 else end_date
        se_date = f"{s}~{e}"

    payload = {
        "pageNum": page_num,
        "pageSize": page_size,
        "column": "",
        "tabName": "fulltext",
        "stock": stock,
        "searchkey": "",
        "category": category,
        "seDate": se_date,
        "sortName": "",
        "sortType": "",
        "isHLtitle": "true",
    }

    try:
        resp = requests.post(_BASE_URL, data=payload, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except (IOError, ConnectionError, TimeoutError, requests.exceptions.RequestException):
        raise
    except Exception as e:
        return {"status": "error", "message": str(e), "data": [], "total_count": 0, "has_more": False}

    try:
        result = resp.json()
    except Exception as e:
        return {"status": "error", "message": f"JSON 解析失败: {e}", "data": [], "total_count": 0, "has_more": False}

    # Fallback: stock 参数查不到时，用 searchkey 重查（部分股票代码格式巨潮不识别）
    if stock and not result.get("announcements"):
        payload_fb = payload.copy()
        payload_fb["stock"] = ""
        payload_fb["searchkey"] = stock
        try:
            time.sleep(0.5)
            resp_fb = requests.post(_BASE_URL, data=payload_fb, headers=_HEADERS, timeout=15)
            resp_fb.raise_for_status()
            result = resp_fb.json()
        except Exception:
            pass

    announcements = result.get("announcements") or []
    total = result.get("totalAnnouncement", 0)

    data = []
    for ann in announcements:
        sec_code = ann.get("secCode", "")
        ann_time = ann.get("announcementTime", 0)
        if ann_time:
            from datetime import datetime
            ann_date = datetime.fromtimestamp(ann_time / 1000).strftime("%Y%m%d")
        else:
            ann_date = ""

        adjunct_url = ann.get("adjunctUrl", "")
        pdf_url = f"{_PDF_BASE}{adjunct_url}" if adjunct_url else ""

        data.append({
            "ts_code": sec_code,
            "ann_date": ann_date,
            "title": ann.get("announcementTitle", "").replace("<em>", "").replace("</em>", ""),
            "category": ann.get("announcementTypeName", ""),
            "pdf_url": pdf_url,
        })

    return {
        "status": "ok",
        "data": data,
        "total_count": total,
        "has_more": page_num * page_size < total,
    }


def query_all_announcements(stock: str = "", start_date: str = "", end_date: str = "",
                            category: str = "", max_pages: int = 100) -> list[dict]:
    """分页拉取全部公告（自动翻页）。"""
    all_data = []
    for page in range(1, max_pages + 1):
        result = query_announcements(stock=stock, start_date=start_date, end_date=end_date,
                                     category=category, page_num=page, page_size=30)
        if result["status"] != "ok" or not result["data"]:
            break
        all_data.extend(result["data"])
        if not result["has_more"]:
            break
        time.sleep(1)
    return all_data


def download_announcement_pdf(pdf_url: str) -> bytes | None:
    """下载公告 PDF 文件。返回 bytes 或 None。"""
    try:
        resp = requests.get(pdf_url, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
        if resp.headers.get("Content-Type", "").startswith("application/pdf"):
            return resp.content
        return None
    except Exception:
        return None


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """从 PDF bytes 提取纯文本。"""
    try:
        import pdfplumber
        import io
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            texts = []
            for page in pdf.pages[:20]:
                text = page.extract_text()
                if text:
                    texts.append(text)
            return "\n".join(texts)
    except Exception:
        return ""


def fetch_announcement_text(pdf_url: str) -> str:
    """一步到位：下载PDF -> 提取文本。"""
    pdf_bytes = download_announcement_pdf(pdf_url)
    if not pdf_bytes:
        return ""
    return extract_text_from_pdf(pdf_bytes)
