"""Tushare Pro SDK 客户端封装。"""

from __future__ import annotations

import time
import tushare as ts
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from vault.proxy import get_credential

_RETRY_DECORATOR = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=3, max=30),
    retry=retry_if_exception_type((IOError, ConnectionError, TimeoutError, OSError)),
    reraise=True,
)

_last_call_time = 0.0
_MIN_INTERVAL = 0.3

def _throttle():
    """API 调用频率限制：最少间隔 _MIN_INTERVAL 秒。"""
    global _last_call_time
    elapsed = time.time() - _last_call_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_call_time = time.time()

_pro: ts.DataApi | None = None


def _get_pro() -> ts.DataApi:
    """懒加载 tushare pro_api 实例，调用前自动限频。"""
    global _pro
    _throttle()
    if _pro is None:
        token = get_credential("tushare")
        _pro = ts.pro_api(token)
    return _pro


@_RETRY_DECORATOR
def get_daily(ts_code: str, start_date: str, end_date: str) -> dict:
    """获取日线行情。"""
    pro = _get_pro()
    try:
        df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_income(ts_code: str, period: str) -> dict:
    """获取利润表。"""
    pro = _get_pro()
    try:
        df = pro.income(ts_code=ts_code, period=period)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


# ---------------------------------------------------------------------------
# Fundamental Agent
# ---------------------------------------------------------------------------


@_RETRY_DECORATOR
def get_balancesheet(ts_code: str, period: str) -> dict:
    """获取资产负债表。"""
    pro = _get_pro()
    try:
        df = pro.balancesheet(ts_code=ts_code, period=period)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_cashflow(ts_code: str, period: str) -> dict:
    """获取现金流量表。"""
    pro = _get_pro()
    try:
        df = pro.cashflow(ts_code=ts_code, period=period)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_fina_indicator(ts_code: str, period: str) -> dict:
    """获取财务指标。"""
    pro = _get_pro()
    try:
        df = pro.fina_indicator(ts_code=ts_code, period=period)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_forecast(ts_code: str) -> dict:
    """获取业绩预告。"""
    pro = _get_pro()
    try:
        df = pro.forecast(ts_code=ts_code)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


# ---------------------------------------------------------------------------
# Technical Agent
# ---------------------------------------------------------------------------


@_RETRY_DECORATOR
def get_daily_basic(ts_code: str, start_date: str, end_date: str) -> dict:
    """获取每日指标（换手率、PE、PB 等）。"""
    pro = _get_pro()
    try:
        df = pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_adj_factor(ts_code: str, start_date: str, end_date: str) -> dict:
    """获取复权因子。"""
    pro = _get_pro()
    try:
        df = pro.adj_factor(ts_code=ts_code, start_date=start_date, end_date=end_date)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


# ---------------------------------------------------------------------------
# Event Agent
# ---------------------------------------------------------------------------


@_RETRY_DECORATOR
def get_share_float(ts_code: str) -> dict:
    """获取限售股解禁。"""
    pro = _get_pro()
    try:
        df = pro.share_float(ts_code=ts_code)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_stk_holdertrade(ts_code: str, start_date: str, end_date: str) -> dict:
    """获取股东增减持。"""
    pro = _get_pro()
    try:
        df = pro.stk_holdertrade(ts_code=ts_code, start_date=start_date, end_date=end_date)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


# ---------------------------------------------------------------------------
# Flow Hot Money Agent
# ---------------------------------------------------------------------------


@_RETRY_DECORATOR
def get_top_list(trade_date: str) -> dict:
    """获取龙虎榜每日明细。"""
    pro = _get_pro()
    try:
        df = pro.top_list(trade_date=trade_date)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_top_inst(trade_date: str) -> dict:
    """获取龙虎榜机构交易明细。"""
    pro = _get_pro()
    try:
        df = pro.top_inst(trade_date=trade_date)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


# ---------------------------------------------------------------------------
# Flow Institutional Agent
# ---------------------------------------------------------------------------


@_RETRY_DECORATOR
def get_moneyflow_hsgt(start_date: str, end_date: str) -> dict:
    """获取沪深港通资金流向。"""
    pro = _get_pro()
    try:
        df = pro.moneyflow_hsgt(start_date=start_date, end_date=end_date)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


# ---------------------------------------------------------------------------
# Risk Agent
# ---------------------------------------------------------------------------


@_RETRY_DECORATOR
def get_pledge_stat(ts_code: str) -> dict:
    """获取股权质押统计。"""
    pro = _get_pro()
    try:
        df = pro.pledge_stat(ts_code=ts_code)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


# ---------------------------------------------------------------------------
# Research Report Agent
# ---------------------------------------------------------------------------


@_RETRY_DECORATOR
def get_research_report(report_date: str) -> dict:
    """获取券商研报。需显式指定 fields 才能拿到 abstr 摘要字段。"""
    pro = _get_pro()
    try:
        df = pro.research_report(
            report_date=report_date,
            fields="title,report_type,author,name,ts_code,inst_csname,ind_name,abstr,trade_date,url",
        )
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


# ---------------------------------------------------------------------------
# Policy Agent
# ---------------------------------------------------------------------------


@_RETRY_DECORATOR
def get_npr(org: str = "", start_date: str = "", end_date: str = "", ptype: str = "", fields: str = "") -> dict:
    """获取国家政策法规。fields 为空时使用默认字段（含正文）。"""
    pro = _get_pro()
    try:
        kwargs: dict[str, str] = {}
        if org:
            kwargs["org"] = org
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        if ptype:
            kwargs["ptype"] = ptype
        if fields:
            kwargs["fields"] = fields
        else:
            kwargs["fields"] = "pubtime,title,url,content_html,pcode,puborg,ptype"
        df = pro.npr(**kwargs)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


# ---------------------------------------------------------------------------
# Flow Hot Money Agent — Seats
# ---------------------------------------------------------------------------


@_RETRY_DECORATOR
def get_hm_list() -> dict:
    """获取游资名录（500+知名游资+营业部映射+风格描述）。"""
    pro = _get_pro()
    try:
        df = pro.hm_list()
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_block_trade(trade_date: str) -> dict:
    """获取大宗交易（含买卖营业部）。"""
    pro = _get_pro()
    try:
        df = pro.block_trade(trade_date=trade_date)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


# ---------------------------------------------------------------------------
# Sector / Survey Agent
# ---------------------------------------------------------------------------


@_RETRY_DECORATOR
def get_anns_d(ts_code: str, start_date: str, end_date: str) -> dict:
    """获取公告元数据。"""
    pro = _get_pro()
    try:
        df = pro.anns_d(ts_code=ts_code, start_date=start_date, end_date=end_date)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_ths_index(exchange: str = "", type: str = "N") -> dict:
    """获取同花顺板块指数。"""
    pro = _get_pro()
    try:
        df = pro.ths_index(exchange=exchange, type=type)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_ths_member(ts_code: str) -> dict:
    """获取同花顺板块成分。"""
    pro = _get_pro()
    try:
        df = pro.ths_member(ts_code=ts_code)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_stk_surv(ts_code: str) -> dict:
    """获取机构调研。"""
    pro = _get_pro()
    try:
        df = pro.stk_surv(ts_code=ts_code)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


# ---------------------------------------------------------------------------
# V2-A 新增接口
# ---------------------------------------------------------------------------


@_RETRY_DECORATOR
def get_moneyflow_ind_ths(trade_date: str) -> dict:
    """获取同花顺行业资金流。"""
    pro = _get_pro()
    try:
        df = pro.moneyflow_ind_ths(trade_date=trade_date)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_moneyflow_cnt_ths(trade_date: str) -> dict:
    """获取同花顺概念资金流。"""
    pro = _get_pro()
    try:
        df = pro.moneyflow_cnt_ths(trade_date=trade_date)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_fina_mainbz(ts_code: str, period: str, type: str = "") -> dict:
    """获取主营业务构成。type: P=按产品 D=按地区，空=全部。"""
    pro = _get_pro()
    try:
        kwargs: dict[str, str] = {"ts_code": ts_code, "period": period}
        if type:
            kwargs["type"] = type
        df = pro.fina_mainbz(**kwargs)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_stk_holdernumber(ts_code: str, start_date: str = "", end_date: str = "") -> dict:
    """获取股东户数。"""
    pro = _get_pro()
    try:
        kwargs = {"ts_code": ts_code}
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        df = pro.stk_holdernumber(**kwargs)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_forecast_vip(date: str) -> dict:
    """获取全市场业绩预告（VIP）。"""
    pro = _get_pro()
    try:
        df = pro.forecast_vip(ann_date=date)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_express_vip(date: str) -> dict:
    """获取全市场业绩快报（VIP）。"""
    pro = _get_pro()
    try:
        df = pro.express_vip(ann_date=date)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_limit_list_d(trade_date: str) -> dict:
    """获取涨跌停明细。"""
    pro = _get_pro()
    try:
        df = pro.limit_list_d(trade_date=trade_date)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_margin(trade_date: str) -> dict:
    """获取融资融券交易汇总。"""
    pro = _get_pro()
    try:
        df = pro.margin(trade_date=trade_date)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_margin_detail(ts_code: str, start_date: str = "", end_date: str = "") -> dict:
    """获取融资融券交易明细。"""
    pro = _get_pro()
    try:
        kwargs = {"ts_code": ts_code}
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        df = pro.margin_detail(**kwargs)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_hsgt_top10(trade_date: str) -> dict:
    """获取沪深股通十大成交股。"""
    pro = _get_pro()
    try:
        df = pro.hsgt_top10(trade_date=trade_date)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_top10_holders(ts_code: str, period: str = "") -> dict:
    """获取前十大股东。"""
    pro = _get_pro()
    try:
        kwargs = {"ts_code": ts_code}
        if period:
            kwargs["period"] = period
        df = pro.top10_holders(**kwargs)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_moneyflow(ts_code: str = "", trade_date: str = "") -> dict:
    """获取个股资金流向（大单/中单/小单/特大单）。"""
    pro = _get_pro()
    try:
        kwargs: dict = {}
        if ts_code:
            kwargs["ts_code"] = ts_code
        if trade_date:
            kwargs["trade_date"] = trade_date
        df = pro.moneyflow(**kwargs)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_research_report_by_stock(ts_code: str, start_date: str = "", end_date: str = "") -> dict:
    """按个股获取券商研报。"""
    pro = _get_pro()
    try:
        kwargs: dict[str, str] = {
            "ts_code": ts_code,
            "fields": "title,report_type,author,name,ts_code,inst_csname,ind_name,abstr,trade_date,url",
        }
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        df = pro.research_report(**kwargs)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_index_daily(ts_code: str, start_date: str, end_date: str) -> dict:
    """获取指数日线行情。"""
    pro = _get_pro()
    try:
        df = pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }


@_RETRY_DECORATOR
def get_stock_basic(list_status: str = "L") -> dict:
    """获取股票基础信息（全市场快照）。

    Args:
        list_status: 上市状态。L=上市（默认）、D=退市、P=暂停上市

    Returns:
        {"status": "ok", "data": [{ts_code, symbol, name, area, industry, market, list_date}, ...]}
    """
    pro = _get_pro()
    try:
        df = pro.stock_basic(
            list_status=list_status,
            fields="ts_code,symbol,name,area,industry,market,list_date",
        )
        return {"status": "ok", "data": df.to_dict("records")}
    except (IOError, ConnectionError, TimeoutError):
        raise
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TUSHARE_API_ERROR",
            "message": str(e),
            "retry_hint": False,
        }
