"""统一数据访问入口。tushare + akshare 双源路由。"""

from __future__ import annotations

from sandboxes.data import tushare_client, akshare_client

_TUSHARE_ROUTES: set[str] = {
    "get_daily",
    "get_income",
    "get_balancesheet",
    "get_cashflow",
    "get_fina_indicator",
    "get_forecast",
    "get_daily_basic",
    "get_adj_factor",
    "get_share_float",
    "get_stk_holdertrade",
    "get_top_list",
    "get_top_inst",
    "get_moneyflow_hsgt",
    "get_pledge_stat",
    "get_research_report",
    "get_npr",
    "get_hm_list",
    "get_block_trade",
    "get_anns_d",
    "get_ths_index",
    "get_ths_member",
    "get_stk_surv",
    "get_moneyflow_ind_ths",
    "get_moneyflow_cnt_ths",
    "get_fina_mainbz",
    "get_stk_holdernumber",
    "get_forecast_vip",
    "get_express_vip",
    "get_limit_list_d",
    "get_margin",
    "get_margin_detail",
    "get_hsgt_top10",
    "get_top10_holders",
    "get_moneyflow",
    "get_index_daily",
}

_AKSHARE_ROUTES: set[str] = {
    "get_cls_news",
    "get_north_flow_individual",
    "get_jin10_news",
}


def execute(source: str, api_name: str, params: dict) -> dict:
    """统一数据访问入口。

    source: "data"（当前固定）
    api_name: tushare 或 akshare 的函数名
    params: 传给对应函数的参数 dict
    """
    if source != "data":
        return {
            "status": "error",
            "error_code": "UNKNOWN_SOURCE",
            "message": f"Unknown source: {source!r}, expected 'data'",
        }
    if api_name in _TUSHARE_ROUTES:
        handler = getattr(tushare_client, api_name)
        return handler(**params)
    if api_name in _AKSHARE_ROUTES:
        handler = getattr(akshare_client, api_name)
        return handler(**params)
    return {
        "status": "error",
        "error_code": "UNKNOWN_API",
        "message": f"Unknown api_name: {api_name!r}",
    }
