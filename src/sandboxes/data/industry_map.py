"""产业链节点映射模块。MVP 版本：hardcode 关键词→产业链映射 + fina_mainbz 关键词提取。"""
from __future__ import annotations

import time

from sandboxes.data import tushare_client
from sandboxes.data.duckdb_store import query_safe

_DB = "data/duckdb/market.duckdb"

# ---------------------------------------------------------------------------
# 关键词 → 产业链映射字典（MVP hardcode，覆盖热门产业链）
# ---------------------------------------------------------------------------

_INDUSTRY_CHAIN_MAP: dict[str, dict] = {
    "光模块": {
        "chain": "光通信",
        "position": "midstream",
        "upstream": ["光芯片", "InP衬底"],
        "downstream": ["数据中心", "AI算力"],
    },
    "InP": {
        "chain": "光通信",
        "position": "upstream",
        "upstream": ["锗矿", "磷化铟原料"],
        "downstream": ["光模块", "光芯片"],
    },
    "磷化铟": {
        "chain": "光通信",
        "position": "upstream",
        "upstream": ["锗矿"],
        "downstream": ["光模块"],
    },
    "锗": {
        "chain": "半导体材料",
        "position": "upstream",
        "upstream": ["锗矿开采"],
        "downstream": ["红外光学", "光伏", "化合物半导体"],
    },
    "化合物半导体": {
        "chain": "半导体",
        "position": "midstream",
        "upstream": ["InP衬底", "GaAs衬底"],
        "downstream": ["光通信", "5G", "新能源"],
    },
    "算力": {
        "chain": "AI算力",
        "position": "downstream",
        "upstream": ["GPU", "光模块", "服务器"],
        "downstream": ["AI应用", "大模型"],
    },
    "CPO": {
        "chain": "光通信",
        "position": "midstream",
        "upstream": ["光芯片", "硅光"],
        "downstream": ["数据中心"],
    },
    "人形机器人": {
        "chain": "机器人",
        "position": "midstream",
        "upstream": ["减速器", "伺服电机", "传感器"],
        "downstream": ["制造业", "服务业"],
    },
    "固态电池": {
        "chain": "新能源",
        "position": "midstream",
        "upstream": ["电解质", "锂盐"],
        "downstream": ["电动车", "储能"],
    },
    "HBM": {
        "chain": "AI算力",
        "position": "upstream",
        "upstream": ["DRAM晶圆", "先进封装"],
        "downstream": ["GPU", "AI训练"],
    },
    "液冷": {
        "chain": "AI算力",
        "position": "midstream",
        "upstream": ["冷却液", "冷板"],
        "downstream": ["数据中心", "AI服务器"],
    },
    "先进封装": {
        "chain": "半导体",
        "position": "midstream",
        "upstream": ["封装基板", "光刻胶"],
        "downstream": ["HBM", "GPU", "AI芯片"],
    },
    "低轨卫星": {
        "chain": "卫星通信",
        "position": "midstream",
        "upstream": ["卫星制造", "火箭发射"],
        "downstream": ["卫星互联网", "物联网"],
    },
    "减速器": {
        "chain": "机器人",
        "position": "upstream",
        "upstream": ["精密齿轮", "轴承"],
        "downstream": ["工业机器人", "人形机器人"],
    },
    "光芯片": {
        "chain": "光通信",
        "position": "upstream",
        "upstream": ["InP衬底", "外延片"],
        "downstream": ["光模块", "CPO"],
    },
    "硅光": {
        "chain": "光通信",
        "position": "upstream",
        "upstream": ["硅晶圆", "光刻"],
        "downstream": ["CPO", "光模块"],
    },
    "GPU": {
        "chain": "AI算力",
        "position": "midstream",
        "upstream": ["先进封装", "HBM", "EDA"],
        "downstream": ["AI训练", "大模型"],
    },
    "大模型": {
        "chain": "AI应用",
        "position": "midstream",
        "upstream": ["GPU", "算力", "数据"],
        "downstream": ["智能客服", "AI Agent", "自动驾驶"],
    },
    "具身智能": {
        "chain": "机器人",
        "position": "downstream",
        "upstream": ["人形机器人", "传感器", "大模型"],
        "downstream": ["制造业", "服务业"],
    },
    "国产替代": {
        "chain": "半导体",
        "position": "midstream",
        "upstream": ["EDA", "光刻机", "材料"],
        "downstream": ["芯片设计", "晶圆制造"],
    },
}


def _extract_keywords_from_bz(bz_items: list[str]) -> list[str]:
    """从 fina_mainbz 的 bz_item 列表中提取匹配产业链映射的关键词。"""
    matched = []
    for item in bz_items:
        for kw in _INDUSTRY_CHAIN_MAP:
            if kw in item and kw not in matched:
                matched.append(kw)
    return matched


def _build_industry_chain(keywords: list[str]) -> dict[str, list[str]]:
    """根据匹配的关键词列表构建聚合的产业链上下游。"""
    upstream: list[str] = []
    midstream: list[str] = []
    downstream: list[str] = []

    for kw in keywords:
        info = _INDUSTRY_CHAIN_MAP.get(kw)
        if not info:
            continue
        pos = info["position"]
        chain_name = f"{info['chain']}-{kw}"
        if pos == "upstream":
            upstream.append(chain_name)
        elif pos == "midstream":
            midstream.append(chain_name)
        else:
            downstream.append(chain_name)
        for u in info.get("upstream", []):
            if u not in upstream:
                upstream.append(u)
        for d in info.get("downstream", []):
            if d not in downstream:
                downstream.append(d)

    return {
        "upstream": upstream,
        "midstream": midstream,
        "downstream": downstream,
    }


def get_stock_industries(ts_code: str, db_path: str | None = None) -> dict:
    """
    获取股票所属的产业链节点。

    来源 1：DuckDB ths_index_cache 表的概念板块（如果有）
    来源 2：fina_mainbz 的 bz_item 提取核心业务关键词

    返回包含 ths_concepts、mainbz_keywords、industry_chain 的字典。
    """
    db = db_path or _DB

    ths_concepts: list[str] = []
    try:
        rows = query_safe(
            "SELECT \"name\" FROM ths_index_cache "
            "WHERE \"ts_code\" IN ("
            "  SELECT \"ts_code\" FROM ths_member_cache "
            "  WHERE \"code\" = $1"
            ")",
            [ts_code],
            db_path=db,
        )
        ths_concepts = [r["name"] for r in rows if r.get("name")]
    except Exception:
        pass

    bz_items: list[str] = []
    stock_name = ""
    try:
        result = tushare_client.get_fina_mainbz(ts_code=ts_code, period="", type="P")
        time.sleep(0.5)
        if result["status"] == "ok" and result["data"]:
            stock_name = result["data"][0].get("name", "")
            seen: set[str] = set()
            for r in result["data"]:
                item = r.get("bz_item", "")
                if item and item not in seen:
                    bz_items.append(item)
                    seen.add(item)
    except Exception:
        pass

    all_text = bz_items + [stock_name] + ths_concepts
    matched_keywords = _extract_keywords_from_bz(all_text)

    chain = _build_industry_chain(matched_keywords)

    return {
        "ts_code": ts_code,
        "stock_name": stock_name,
        "ths_concepts": ths_concepts,
        "mainbz_keywords": bz_items[:20],
        "matched_chain_keywords": matched_keywords,
        "industry_chain": chain,
    }


def find_related_stocks(industry_keyword: str, db_path: str | None = None) -> list[dict]:
    """
    从产业关键词找相关股票。

    1. 在 _INDUSTRY_CHAIN_MAP 中查找关键词对应的产业链位置
    2. 在 DuckDB ths_index_cache 中找包含该关键词的概念板块
    3. 用 tushare_client.get_ths_member 获取板块成分股
    4. 返回成分股列表
    """
    db = db_path or _DB
    chain_info = _INDUSTRY_CHAIN_MAP.get(industry_keyword, {})
    position = chain_info.get("position", "unknown")

    # 在 ths_index_cache 中找包含该关键词的概念板块
    matched_sectors: list[dict] = []
    try:
        rows = query_safe(
            "SELECT \"ts_code\", \"name\" FROM ths_index_cache "
            "WHERE \"name\" LIKE $1 "
            "LIMIT 5",
            [f"%{industry_keyword}%"],
            db_path=db,
        )
        matched_sectors = rows
    except Exception:
        pass

    stocks: list[dict] = []
    seen_codes: set[str] = set()

    for sector in matched_sectors:
        sector_code = sector.get("ts_code", "")
        if not sector_code:
            continue
        try:
            result = tushare_client.get_ths_member(ts_code=sector_code)
            time.sleep(1)
            if result["status"] == "ok" and result["data"]:
                for m in result["data"]:
                    code = m.get("code", "")
                    if code and code not in seen_codes:
                        seen_codes.add(code)
                        stocks.append({
                            "ts_code": code,
                            "name": m.get("name", ""),
                            "chain_position": position,
                            "source_sector": sector.get("name", ""),
                        })
        except Exception:
            continue

    return stocks
