"""Akshare 数据客户端封装（免费，无需 token）。"""

from __future__ import annotations

import akshare as ak
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((IOError, ConnectionError, TimeoutError)),
    reraise=True,
)
def get_cls_news(count: int = 100) -> dict:
    """获取财联社快讯。

    调用 ak.stock_info_global_cls() 返回最近的快讯。
    返回 {"status": "ok", "data": list[dict]} 或 {"status": "error", ...}
    count 参数：返回最近 N 条（对 DataFrame 做 head(count)）
    """
    try:
        df = ak.stock_info_global_cls()
        df = df.head(count)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "AKSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((IOError, ConnectionError, TimeoutError)),
    reraise=True,
)
def get_north_flow_individual(symbol: str) -> dict:
    """获取北向资金个股数据（hk_hold 停日度后的兜底）。

    调用 ak.stock_hsgt_individual_em(symbol=symbol)
    返回 {"status": "ok", "data": list[dict]} 或 {"status": "error", ...}
    """
    try:
        df = ak.stock_hsgt_individual_em(symbol=symbol)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "AKSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((IOError, ConnectionError, TimeoutError)),
    reraise=True,
)
def get_jin10_news(count: int = 100) -> dict:
    """获取金十快讯（fallback 到新浪全球快讯）。

    akshare 无稳定的金十快讯专用接口，此函数按优先级尝试：
    1. ak.js_news (如果存在)
    2. ak.stock_info_global_sina (新浪全球快讯，列: 时间/内容)
    3. 返回空列表

    返回 {"status": "ok", "data": list[dict]} 或 {"status": "error", ...}
    """
    try:
        if hasattr(ak, "js_news"):
            df = ak.js_news()
        elif hasattr(ak, "stock_info_global_sina"):
            df = ak.stock_info_global_sina()
        else:
            return {"status": "ok", "data": []}
        df = df.head(count)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "AKSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((IOError, ConnectionError, TimeoutError)),
    reraise=True,
)
def get_stock_news_em(symbol: str) -> dict:
    """获取东方财富个股新闻。symbol 为 6 位股票代码。"""
    try:
        df = ak.stock_news_em(symbol=symbol)
        df = df.head(30)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "AKSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }
