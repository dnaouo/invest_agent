"""Agent Tool 定义 — OpenAI 格式 schema + 实现函数。"""
from __future__ import annotations

from sandboxes.data.duckdb_store import query
from sandboxes.data import tushare_client, akshare_client

_DB = "data/duckdb/market.duckdb"

# ---- Tool 实现函数 ----


def search_reports(keyword: str, days: int = 7, db_path: str | None = None) -> str:
    """按关键词搜索近期研报。返回精简文本。"""
    db = db_path or _DB
    try:
        safe_kw = keyword.replace("'", "")
        rows = query(
            f"SELECT title, inst_csname, report_type, report_date, abstr FROM research_report "
            f"WHERE title LIKE '%{safe_kw}%' OR abstr LIKE '%{safe_kw}%' "
            f"ORDER BY report_date DESC LIMIT 10",
            db_path=db,
        )
        if not rows:
            return f"未找到包含'{keyword}'的研报"
        lines = []
        for r in rows:
            abstr = str(r.get("abstr", ""))[:200]
            lines.append(f"[{r.get('report_date','')}] {r.get('inst_csname','')} | {r.get('report_type','')} | {r.get('title','')} | {abstr}")
        return "\n".join(lines)
    except Exception as e:
        return f"研报查询失败: {e}"


def search_policy(keyword: str, db_path: str | None = None) -> str:
    """按关键词搜索政策法规。"""
    db = db_path or _DB
    try:
        safe_kw = keyword.replace("'", "")
        rows = query(
            f"SELECT title, org, pub_date FROM policy "
            f"WHERE title LIKE '%{safe_kw}%' ORDER BY pub_date DESC LIMIT 10",
            db_path=db,
        )
        if not rows:
            return f"未找到包含'{keyword}'的政策"
        return "\n".join(f"[{r.get('pub_date','')}] {r.get('org','')} | {r.get('title','')}" for r in rows)
    except Exception as e:
        return f"政策查询失败: {e}"


def match_hot_money(trade_date: str, db_path: str | None = None) -> str:
    """龙虎榜 x 游资名录预匹配：返回当日游资动向。"""
    db = db_path or _DB
    try:
        rows = query(
            f"SELECT t.ts_code, t.exalter, t.buy, t.sell, h.hm_name "
            f"FROM top_list t "
            f"JOIN hm_list h ON t.exalter = h.broker "
            f"WHERE t.trade_date = '{trade_date}' "
            f"ORDER BY t.buy DESC LIMIT 20",
            db_path=db,
        )
        if not rows:
            return f"{trade_date} 无知名游资席位命中龙虎榜"
        lines = []
        for r in rows:
            action = "买入" if (r.get("buy", 0) or 0) > (r.get("sell", 0) or 0) else "卖出"
            amt = max(r.get("buy", 0) or 0, r.get("sell", 0) or 0)
            lines.append(f"游资{r.get('hm_name','')} 通过{r.get('exalter','')} {action} {r.get('ts_code','')} {amt:.0f}万")
        return "\n".join(lines)
    except Exception as e:
        return f"游资匹配查询失败: {e}"


def get_north_individual(ts_code: str, db_path: str | None = None) -> str:
    """查询个股北向持仓（带时效性检查）。"""
    try:
        symbol = ts_code.split(".")[0]
        result = akshare_client.get_north_flow_individual(symbol=symbol)
        if result["status"] != "ok" or not result["data"]:
            return f"{ts_code} 无北向个股持仓数据"
        data = result["data"]
        dates = [str(r.get("date", "")) for r in data if r.get("date")]
        latest = max(dates) if dates else "未知"
        note = ""
        if latest < "2025":
            note = f"[警告] 数据严重过期（最新{latest}），仅供参考。"
        top5 = sorted(data, key=lambda x: str(x.get("date", "")), reverse=True)[:5]
        lines = [note] if note else []
        for r in top5:
            lines.append(f"[{r.get('date','')}] 持股{r.get('shareholding','')}股, 市值{r.get('close_amt','')}万")
        return "\n".join(lines) or "无数据"
    except Exception as e:
        return f"北向个股查询失败: {e}"


def search_news(keyword: str, count: int = 10, db_path: str | None = None) -> str:
    """按关键词搜索快讯。"""
    db = db_path or _DB
    try:
        safe_kw = keyword.replace("'", "")
        rows = query(f"SELECT * FROM news LIMIT {count}", db_path=db)
        if not rows:
            return "快讯库为空"
        matched = [r for r in rows if safe_kw in str(r)][:count]
        if not matched:
            return f"未找到包含'{keyword}'的快讯"
        lines = []
        for r in matched:
            title = r.get("标题", r.get("title", str(r)[:100]))
            time = r.get("发布时间", r.get("time", ""))
            source = r.get("source", "")
            lines.append(f"[{time}] [{source}] {title}")
        return "\n".join(lines)
    except Exception as e:
        return f"快讯查询失败: {e}"


def get_theme_members(theme_name: str) -> str:
    """查询同花顺板块成分股。"""
    try:
        idx = tushare_client.get_ths_index()
        if idx["status"] != "ok":
            return "板块指数查询失败"
        matched = [r for r in idx["data"] if theme_name in str(r.get("name", ""))]
        if not matched:
            return f"未找到包含'{theme_name}'的板块"
        ts_code = matched[0].get("ts_code", "")
        members = tushare_client.get_ths_member(ts_code=ts_code)
        if members["status"] != "ok":
            return f"板块{ts_code}成分股查询失败"
        lines = [f"板块: {matched[0].get('name','')} ({ts_code})", "成分股:"]
        for m in members["data"][:20]:
            lines.append(f"  {m.get('code','')} {m.get('name','')}")
        return "\n".join(lines)
    except Exception as e:
        return f"板块查询失败: {e}"


def classify_events(ts_code: str, days: int = 30) -> str:
    """结构化事件分类。"""
    try:
        from sandboxes.data.events_db import classify_events as _classify
        from datetime import datetime, timedelta
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        events = _classify(ts_code, start, end)
        if not events:
            return f"{ts_code} 近{days}天无结构化事件"
        lines = []
        for e in events[:10]:
            lines.append(f"[{e.get('ann_date','')}] {e.get('event_type','')} 强度{e.get('strength',0):.1f} | {e.get('detail','')[:100]}")
        return "\n".join(lines)
    except Exception as e:
        return f"事件分类失败: {e}"


# ---- Tool Schema（OpenAI 格式，供 Kimi tool calling 用）----

TOOL_SEARCH_REPORTS = {
    "type": "function",
    "function": {
        "name": "search_reports",
        "description": "按股票名称或行业关键词搜索近期券商研报摘要。返回评级、目标价、核心观点。用于交叉验证基本面判断或发现市场共识。",
        "parameters": {"type": "object", "properties": {"keyword": {"type": "string", "description": "股票简称或行业关键词"}}, "required": ["keyword"]},
    },
}

TOOL_SEARCH_POLICY = {
    "type": "function",
    "function": {
        "name": "search_policy",
        "description": "按关键词搜索国家政策法规（来源：国务院、各部委公开文件）。用于判断政策驱动主线。",
        "parameters": {"type": "object", "properties": {"keyword": {"type": "string", "description": "政策关键词如'半导体'、'新能源'"}}, "required": ["keyword"]},
    },
}

TOOL_MATCH_HOT_MONEY = {
    "type": "function",
    "function": {
        "name": "match_hot_money",
        "description": "查询当日龙虎榜与知名游资名录的匹配结果。返回'游资X通过Y营业部买入Z股N万'的预匹配结果。",
        "parameters": {"type": "object", "properties": {"trade_date": {"type": "string", "description": "交易日期YYYYMMDD"}}, "required": ["trade_date"]},
    },
}

TOOL_GET_NORTH = {
    "type": "function",
    "function": {
        "name": "get_north_individual",
        "description": "查询个股北向资金持仓变化（带数据时效性检查）。注意：数据可能滞后。",
        "parameters": {"type": "object", "properties": {"ts_code": {"type": "string", "description": "股票代码如000988.SZ"}}, "required": ["ts_code"]},
    },
}

TOOL_SEARCH_NEWS = {
    "type": "function",
    "function": {
        "name": "search_news",
        "description": "按关键词搜索财联社+金十快讯。用于捕捉实时热点和事件催化。",
        "parameters": {"type": "object", "properties": {"keyword": {"type": "string", "description": "搜索关键词"}}, "required": ["keyword"]},
    },
}

TOOL_GET_THEME = {
    "type": "function",
    "function": {
        "name": "get_theme_members",
        "description": "查询同花顺概念/行业板块的成分股列表。用于从主题推导受益标的。",
        "parameters": {"type": "object", "properties": {"theme_name": {"type": "string", "description": "板块名称如'CPO'、'光模块'"}}, "required": ["theme_name"]},
    },
}

TOOL_CLASSIFY_EVENTS = {
    "type": "function",
    "function": {
        "name": "classify_events",
        "description": "对指定股票做结构化事件分类（业绩预告/解禁/增减持等），返回事件类型和强度评分。",
        "parameters": {"type": "object", "properties": {"ts_code": {"type": "string", "description": "股票代码"}, "days": {"type": "integer", "description": "近N天，默认30", "default": 30}}, "required": ["ts_code"]},
    },
}

ALL_TOOLS = [TOOL_SEARCH_REPORTS, TOOL_SEARCH_POLICY, TOOL_MATCH_HOT_MONEY, TOOL_GET_NORTH, TOOL_SEARCH_NEWS, TOOL_GET_THEME, TOOL_CLASSIFY_EVENTS]

TOOL_FUNCTIONS = {
    "search_reports": search_reports,
    "search_policy": search_policy,
    "match_hot_money": match_hot_money,
    "get_north_individual": get_north_individual,
    "search_news": search_news,
    "get_theme_members": get_theme_members,
    "classify_events": classify_events,
}
