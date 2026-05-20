"""假设驱动分析引擎 — 四阶段分析流程：快速扫描 → 针对性取证 → 逻辑判断 → Critic 审查。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from agents.hypothesis_critic import hypothesis_critic_node
from llm_clients.kimi_sync import call_kimi
from llm_clients.tier_router import get_tier_config
from sandboxes.data import tushare_client
from tools.agent_tools import (
    ALL_TOOLS,
    TOOL_FUNCTIONS,
    fetch_announcement_content,
    get_mainbiz_detail,
    get_report_rating,
    get_industry_chain,
    search_reports,
    fetch_stock_news,
)
from tools.consensus import build_consensus
from tools.news_search import extract_mainbz_keywords, search_news_for_stock
from tools.tool_executor import run_agent_with_tools

log = logging.getLogger(__name__)

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "agents" / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPT_DIR / name).read_text(encoding="utf-8")


def _subtract_days(date_str: str, days: int) -> str:
    dt = datetime.strptime(date_str, "%Y%m%d")
    return (dt - timedelta(days=days)).strftime("%Y%m%d")


def _extract_json(text: str) -> dict | None:
    """从 LLM 输出中提取 JSON 对象，兼容 markdown code fence 和多余文本。"""
    if not text or not text.strip():
        return None

    import re
    # 策略 1：提取 ```json ... ``` 或 ``` ... ``` 内的 JSON
    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if fence_match:
        candidate = fence_match.group(1).strip()
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    # 策略 2：找最外层 { ... }
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        obj = json.loads(text[start:end])
        if isinstance(obj, dict):
            return obj
    except (ValueError, json.JSONDecodeError):
        pass

    # 策略 3：逐字符配对大括号，找最大的合法 JSON 块
    depth = 0
    json_start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                json_start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and json_start >= 0:
                try:
                    obj = json.loads(text[json_start:i + 1])
                    if isinstance(obj, dict) and ("verifications" in obj or "hypothesis" in obj or "confidence" in obj):
                        return obj
                except json.JSONDecodeError:
                    json_start = -1

    return None


def _fetch_phase1_data(ts_code: str, trade_date: str, stock_name: str = "") -> dict:
    """拉取 Phase 1 需要的轻量数据：最新 1 期财报摘要 + daily_basic + 板块 + 行业新闻。"""
    data: dict = {}

    year = trade_date[:4]
    period = f"{int(year) - 1}1231"

    try:
        fina = tushare_client.get_fina_indicator(ts_code=ts_code, period=period)
        if fina["status"] == "ok" and fina["data"]:
            data["fina_indicator"] = fina["data"][0]
    except Exception:
        pass

    start = _subtract_days(trade_date, 30)
    try:
        db = tushare_client.get_daily_basic(
            ts_code=ts_code, start_date=start, end_date=trade_date,
        )
        if db["status"] == "ok" and db["data"]:
            data["daily_basic"] = db["data"][0]
    except Exception:
        pass

    try:
        idx = tushare_client.get_ths_index()
        if idx["status"] == "ok" and idx["data"]:
            code_prefix = ts_code.split(".")[0]
            matched = []
            for item in idx["data"][:200]:
                try:
                    members = tushare_client.get_ths_member(ts_code=item.get("ts_code", ""))
                    if members["status"] == "ok":
                        for m in members["data"]:
                            if code_prefix in str(m.get("code", "")):
                                matched.append(item.get("name", ""))
                                break
                except Exception:
                    continue
                if len(matched) >= 3:
                    break
            if matched:
                data["sectors"] = matched
    except Exception:
        pass

    try:
        consensus = build_consensus(ts_code)
        if consensus.get("coverage_count", 0) > 0:
            data["consensus"] = consensus
    except Exception:
        pass

    try:
        from sandboxes.data.duckdb_store import query_safe
        start_ann = _subtract_days(trade_date, 30)
        code6 = ts_code.split(".")[0]
        ann_rows = query_safe(
            "SELECT ann_date, title, category FROM announcements "
            "WHERE ts_code LIKE $1 AND ann_date >= $2 "
            "ORDER BY ann_date DESC LIMIT 10",
            [f"%{code6}%", start_ann],
            db_path=None,
        )
        if ann_rows:
            data["recent_announcements"] = ann_rows
    except Exception:
        pass

    try:
        mainbz_kws: list[str] = []
        mainbz = tushare_client.get_fina_mainbz(ts_code=ts_code, period=period, type="P")
        if mainbz["status"] == "ok" and mainbz["data"]:
            mainbz_kws = extract_mainbz_keywords(mainbz["data"])
        news_result = search_news_for_stock(
            ts_code=ts_code,
            stock_name=stock_name or ts_code,
            mainbz_keywords=mainbz_kws,
            days=7,
        )
        if news_result["news_count"] > 0:
            data["related_news"] = {
                "summary": news_result["summary"],
                "keywords_used": news_result["keywords_used"][:10],
                "news_count": news_result["news_count"],
                "top_news": [
                    {"title": n["title"], "time": n["time"], "source": n["source"]}
                    for n in news_result["news"][:10]
                ],
            }
    except Exception:
        pass

    return data


def _fetch_phase2_data(
    ts_code: str, trade_date: str, stock_name: str, phase1_data: dict,
) -> dict:
    """结构化信息收集——在 LLM 搜索前自动收集关键数据。"""
    pack: dict[str, str] = {}

    # 1. 逐个读取近期公告全文（最多 5 条，跳过定期报告）
    for ann in phase1_data.get("recent_announcements", [])[:5]:
        title = ann.get("title", "")
        if not title or "定期报告" in str(ann.get("category", "")):
            continue
        try:
            content = fetch_announcement_content(ts_code, title[:8])
            if content and len(content) > 100 and "未查到" not in content:
                pack[f"公告全文: {title[:30]}"] = content[:2000]
        except Exception:
            pass

    # 2. 主营业务构成
    try:
        mainbiz = get_mainbiz_detail(ts_code)
        if mainbiz and "无主营" not in mainbiz:
            pack["主营业务构成"] = mainbiz
    except Exception:
        pass

    # 3. 评级历史
    try:
        ratings = get_report_rating(ts_code, days=365)
        if ratings and "无研报评级" not in ratings:
            pack["券商评级"] = ratings
    except Exception:
        pass

    # 4. 产业链 → 提取行业关键词 → 搜行业研报
    try:
        chain_text = get_industry_chain(ts_code)
        if chain_text and "查询失败" not in chain_text:
            pack["产业链"] = chain_text
            keywords_to_search: list[str] = []
            for line in chain_text.split("\n"):
                if "匹配产业链关键词" in line:
                    kws = line.split(":")[-1].strip().split(",")
                    keywords_to_search.extend([k.strip() for k in kws[:3]])
                if "下游" in line:
                    downs = line.split(":")[-1].strip().split(",")
                    keywords_to_search.extend([d.strip() for d in downs[:2]])

            for kw in keywords_to_search[:4]:
                if kw and len(kw) >= 2:
                    try:
                        result = search_reports(kw)
                        if result and "未找到" not in result:
                            pack[f"行业研报({kw})"] = result[:1500]
                    except Exception:
                        pass
    except Exception:
        pass

    # 5. 个股新闻
    try:
        news = fetch_stock_news(ts_code, stock_name)
        if news and "无个股新闻" not in news[:30]:
            pack["个股新闻"] = news[:1500]
    except Exception:
        pass

    log.info("Phase 2 研究资料包: %d 项 (%s)", len(pack), ", ".join(pack.keys()))
    return pack


def _run_phase1(
    ts_code: str,
    trade_date: str,
    stock_name: str,
    trigger_reason: str,
    phase1_data: dict,
) -> dict:
    """Phase 1：快速扫描，输出投资假设 + 3 个关键问题。"""
    system_prompt = _load_prompt("hypothesis_phase1.md")
    user_message = (
        f"股票：{stock_name}（{ts_code}），交易日期：{trade_date}\n"
        f"触发原因：{trigger_reason}\n\n"
        f"基础数据：\n{json.dumps(phase1_data, ensure_ascii=False, default=str)}"
    )

    tier = get_tier_config("hypothesis_scan")
    response = call_kimi(messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ], **tier)

    content = response.get("content", "")
    result = _extract_json(content)

    if result is None:
        result = {
            "hypothesis": f"{stock_name} 需要进一步研究",
            "questions": [
                f"{stock_name} 的核心业务逻辑是什么？",
                f"{stock_name} 的营收增速趋势如何？",
                f"{stock_name} 所处行业的竞争格局？",
            ],
            "stock_type": "industry_logic",
        }

    for key in ("hypothesis", "questions", "stock_type"):
        if key not in result:
            if key == "hypothesis":
                result[key] = f"{stock_name} 需要进一步研究"
            elif key == "questions":
                result[key] = ["业务逻辑？", "增速趋势？", "竞争格局？"]
            else:
                result[key] = "industry_logic"

    return result


def _summarize_tool_evidence(tool_calls_made: list[dict]) -> str:
    """将 tool_calls_made 中的结果拼成可读文本，供 LLM 结构化或 Phase 3 使用。"""
    if not tool_calls_made:
        return ""
    lines = []
    for tc in tool_calls_made:
        name = tc.get("name", "")
        result = tc.get("result", "")
        if result and len(result) > 10:
            lines.append(f"[{name}] {result}")
    return "\n---\n".join(lines)


def _llm_structure_verifications(
    questions: list[str],
    raw_content: str,
    tool_evidence: str,
) -> dict | None:
    """当 Phase 2 JSON 解析失败时，用 LLM 做一次总结+结构化。"""
    questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
    prompt = (
        "你是数据整理助手。下面是一次研究调查的原始输出和工具返回的证据。\n"
        "请将它们整理成严格 JSON 格式。不要输出 JSON 以外的任何文字。\n\n"
        f"待验证问题：\n{questions_text}\n\n"
        f"原始分析文本：\n{raw_content[:3000]}\n\n"
        f"工具返回的证据（关键数据）：\n{tool_evidence[:4000]}\n\n"
        '输出格式：\n{"verifications": [{"question": "原始问题", '
        '"verdict": "supported|refuted|inconclusive", '
        '"evidence": "具体证据", "data_sources": ["工具名"]}]}'
    )
    tier = get_tier_config("hypothesis_scan")
    try:
        resp = call_kimi(messages=[{"role": "user", "content": prompt}], **tier)
        return _extract_json(resp.get("content", ""))
    except Exception:
        return None


def _run_phase2(
    ts_code: str,
    trade_date: str,
    stock_name: str,
    phase1_result: dict,
    phase1_data: dict | None = None,
) -> dict:
    """Phase 2：针对性取证，使用 tools 获取数据验证假设。"""
    system_prompt = _load_prompt("hypothesis_phase2.md")

    questions_text = "\n".join(
        f"{i+1}. {q}" for i, q in enumerate(phase1_result.get("questions", []))
    )

    # 收集研究资料包
    research_pack: dict[str, str] = {}
    if phase1_data:
        try:
            research_pack = _fetch_phase2_data(ts_code, trade_date, stock_name, phase1_data)
        except Exception as exc:
            log.warning("_fetch_phase2_data 异常: %s", exc)

    pack_text = ""
    if research_pack:
        pack_sections = []
        for key, value in research_pack.items():
            pack_sections.append(f"### {key}\n{value}")
        pack_text = "\n\n---\n\n".join(pack_sections)

    user_message = (
        f"股票：{stock_name}（{ts_code}），交易日期：{trade_date}\n\n"
        f"投资假设：{phase1_result.get('hypothesis', '')}\n\n"
        f"待验证问题：\n{questions_text}"
    )
    if pack_text:
        user_message += f"\n\n---\n\n## 已自动收集的研究资料包\n\n{pack_text}"

    tier = get_tier_config("hypothesis_verify")

    response = run_agent_with_tools(
        system_prompt=system_prompt,
        user_message=user_message,
        tools=ALL_TOOLS,
        tool_functions=TOOL_FUNCTIONS,
        tier_config=tier,
        max_rounds=5,
    )

    content = response.get("content", "")
    tool_calls_made = response.get("tool_calls_made", [])
    result = _extract_json(content)

    # Fallback 1: JSON 解析失败但有原始 content + tool 证据 → 用 LLM 结构化
    if result is None and (content.strip() or tool_calls_made):
        questions = phase1_result.get("questions", [])
        tool_evidence = _summarize_tool_evidence(tool_calls_made)
        result = _llm_structure_verifications(questions, content, tool_evidence)

    # Fallback 2: 仍然失败 → 从 tool_calls_made 构建基础验证结果
    if result is None:
        questions = phase1_result.get("questions", [])
        tool_evidence = _summarize_tool_evidence(tool_calls_made)
        result = {
            "verifications": [
                {
                    "question": q,
                    "verdict": "inconclusive",
                    "evidence": "JSON 解析失败，原始工具证据见 raw_tool_evidence",
                    "data_sources": [tc.get("name", "") for tc in tool_calls_made],
                }
                for q in questions
            ],
        }
        if tool_evidence:
            result["raw_tool_evidence"] = tool_evidence[:5000]

    result["tool_calls_made"] = tool_calls_made
    result["_research_pack"] = research_pack
    return result


def _run_phase3(
    ts_code: str,
    stock_name: str,
    phase1_result: dict,
    phase2_result: dict,
    phase1_data: dict,
    research_pack: dict | None = None,
) -> dict:
    """Phase 3：逻辑判断，综合正反证据给出最终结论。"""
    system_prompt = _load_prompt("hypothesis_phase3.md")

    verifications = phase2_result.get("verifications", [])
    ver_text = json.dumps(verifications, ensure_ascii=False, default=str)

    # Phase 2 tool_calls 原始结果（每条取前 300 字）
    tool_calls_made = phase2_result.get("tool_calls_made", [])
    tool_evidence_parts: list[str] = []
    for tc in tool_calls_made:
        name = tc.get("name", "")
        result = tc.get("result", "")
        if result and len(result) > 10:
            tool_evidence_parts.append(f"[{name}] {result[:300]}")
    tool_evidence_summary = "\n---\n".join(tool_evidence_parts)

    # 如果有 raw_tool_evidence（Phase 2 JSON 解析失败时），优先用
    raw_evidence = phase2_result.get("raw_tool_evidence", "")
    if raw_evidence:
        tool_evidence_summary = raw_evidence[:4000]
    elif all(v.get("verdict") == "inconclusive" for v in verifications) and not tool_evidence_summary:
        tool_evidence_summary = _summarize_tool_evidence(tool_calls_made)[:4000]

    basic_info: dict = {}
    if "daily_basic" in phase1_data:
        db = phase1_data["daily_basic"]
        basic_info = {
            "pe_ttm": db.get("pe_ttm"),
            "pb": db.get("pb"),
            "total_mv": db.get("total_mv"),
        }
    if "fina_indicator" in phase1_data:
        fi = phase1_data["fina_indicator"]
        basic_info["roe"] = fi.get("roe")
        basic_info["grossprofit_margin"] = fi.get("grossprofit_margin")

    # 研究资料包摘要（key 列表 + 重要数据项前 200 字）
    pack_summary = ""
    if research_pack:
        pack_parts = []
        for key, value in research_pack.items():
            pack_parts.append(f"### {key}\n{value[:300]}")
        pack_summary = "\n\n".join(pack_parts)

    # fina_mainbz 数据
    mainbz_text = ""
    try:
        fina_mainbz = tushare_client.get_fina_mainbz(ts_code=ts_code, period="", type="P")
        if fina_mainbz["status"] == "ok" and fina_mainbz["data"]:
            bz_lines = []
            for bz in fina_mainbz["data"]:
                name = bz.get("bz_item", "")
                sales = float(bz.get("bz_sales", 0) or 0)
                profit = float(bz.get("bz_profit", 0) or 0)
                margin = (profit / sales * 100) if sales > 0 else 0
                bz_lines.append(f"  {name}: 营收{sales/1e8:.2f}亿, 毛利率{margin:.1f}%")
            mainbz_text = "\n".join(bz_lines)
    except Exception:
        pass

    user_message = (
        f"股票：{stock_name}（{ts_code}）\n\n"
        f"投资假设：{phase1_result.get('hypothesis', '')}\n"
        f"假设类型：{phase1_result.get('stock_type', '')}\n\n"
        f"验证结果：\n{ver_text}\n\n"
        f"基础指标：{json.dumps(basic_info, ensure_ascii=False, default=str)}"
    )
    if mainbz_text:
        user_message += f"\n\n主营业务构成（按产品）：\n{mainbz_text}"
    if tool_evidence_summary:
        user_message += f"\n\nPhase 2 工具调用原始证据：\n{tool_evidence_summary[:4000]}"
    if pack_summary:
        user_message += f"\n\n研究资料包摘要：\n{pack_summary[:4000]}"

    tier = get_tier_config("hypothesis_judge")
    response = call_kimi(messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ], **tier)

    content = response.get("content", "")
    result = _extract_json(content)

    if result is None:
        result = {
            "hypothesis": phase1_result.get("hypothesis", ""),
            "hypothesis_valid": False,
            "confidence": 0.3,
            "evidence_for": [],
            "evidence_against": ["LLM 输出解析失败"],
            "key_risks": ["分析流程异常"],
            "catalyst": "待人工复核",
            "suggestion": "分析流程异常，建议人工复核",
            "position_type": "avoid",
        }

    defaults = {
        "hypothesis": phase1_result.get("hypothesis", ""),
        "hypothesis_valid": False,
        "confidence": 0.3,
        "evidence_for": [],
        "evidence_against": [],
        "key_risks": [],
        "catalyst": "",
        "suggestion": "",
        "position_type": "watch",
        "valuation": {},
        "upgrade_trigger": "",
        "kill_criteria": "",
    }
    for k, v in defaults.items():
        if k not in result:
            result[k] = v

    return result


def _run_critic_followup(
    output: dict,
    ts_code: str,
    trade_date: str,
    stock_name: str,
    phase1_result: dict,
) -> None:
    """Critic 闭环：提取 major unverified challenges，补充查询后合并结果。"""
    critic = output.get("critic", {})
    challenges = critic.get("challenges", [])
    major_unverified = [
        c for c in challenges
        if c.get("unverified") is True and c.get("severity") in ("major", "critical")
    ]
    if len(major_unverified) < 2:
        return

    supplement_qs = [c.get("challenge", "") for c in major_unverified[:3]]
    log.info("Critic 闭环: %d 条 major unverified → 补充查询", len(supplement_qs))

    questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(supplement_qs))
    system_prompt = _load_prompt("hypothesis_phase2.md")
    user_message = (
        f"股票：{stock_name}（{ts_code}），交易日期：{trade_date}\n\n"
        f"投资假设：{phase1_result.get('hypothesis', '')}\n\n"
        f"补充验证问题（来自 Critic 审查）：\n{questions_text}\n\n"
        "请针对以上问题做补充搜索验证。"
    )

    tier = get_tier_config("hypothesis_verify")
    try:
        resp = run_agent_with_tools(
            system_prompt=system_prompt,
            user_message=user_message,
            tools=ALL_TOOLS,
            tool_functions=TOOL_FUNCTIONS,
            tier_config=tier,
            max_rounds=2,
        )
        supplement_content = resp.get("content", "")
        supplement_tools = resp.get("tool_calls_made", [])
        supplement_result = _extract_json(supplement_content)

        output["critic_followup"] = {
            "questions": supplement_qs,
            "tool_calls_made": supplement_tools,
            "result": supplement_result or {"raw_content": supplement_content[:2000]},
        }
        log.info("Critic 闭环完成: %d 次工具调用", len(supplement_tools))
    except Exception as exc:
        log.warning("Critic 闭环补充查询失败: %s", exc)


def run_hypothesis_analysis(
    ts_code: str,
    trade_date: str,
    stock_name: str,
    trigger_reason: str,
) -> dict:
    """假设驱动分析入口。四阶段串行执行，返回完整分析结果。

    返回 dict 包含：
    - phase1: Phase 1 结果（假设 + 问题）
    - phase2: Phase 2 结果（验证结论 + tool 调用记录）
    - phase3: Phase 3 结果（最终判断）
    - critic: Phase 4 结果（逻辑审查）
    - critic_challenges, critic_recommendation, adjusted_confidence
    - data_sources: 所有使用的数据来源
    - error: 如有异常则包含错误信息
    """
    output: dict = {
        "ts_code": ts_code,
        "trade_date": trade_date,
        "stock_name": stock_name,
        "trigger_reason": trigger_reason,
    }

    # M0.3：入口处校验 ts_code / stock_name 一致性，不通过直接 raise（不浪费 12 分钟跑错）
    from tools.symbol_resolver import validate as _validate_symbol, SymbolMismatchError as _SymbolMismatch
    _v = _validate_symbol(ts_code, stock_name)
    if not _v["valid"]:
        raise _SymbolMismatch(
            f"ts_code/name 不一致: {_v['error']}; suggestions: {_v['suggestions']}"
        )

    try:
        phase1_data = _fetch_phase1_data(ts_code, trade_date, stock_name=stock_name)
        output["phase1_data_keys"] = list(phase1_data.keys())
    except Exception as e:
        phase1_data = {}
        output["phase1_data_error"] = str(e)

    try:
        p1 = _run_phase1(ts_code, trade_date, stock_name, trigger_reason, phase1_data)
        output["phase1"] = p1
    except Exception as e:
        output["phase1"] = {
            "hypothesis": f"{stock_name} 分析异常",
            "questions": [],
            "stock_type": "industry_logic",
        }
        output["phase1_error"] = str(e)
        output["phase3"] = {
            "hypothesis_valid": False,
            "confidence": 0.0,
            "position_type": "avoid",
            "suggestion": f"Phase 1 失败: {e}",
        }
        return output

    research_pack: dict[str, str] = {}
    try:
        p2 = _run_phase2(ts_code, trade_date, stock_name, p1, phase1_data=phase1_data)
        output["phase2"] = p2
        research_pack = p2.pop("_research_pack", {})
        output["phase2_research_pack_keys"] = list(research_pack.keys())
    except Exception as e:
        p2 = {"verifications": [], "tool_calls_made": []}
        output["phase2"] = p2
        output["phase2_error"] = str(e)

    try:
        p3 = _run_phase3(ts_code, stock_name, p1, p2, phase1_data, research_pack=research_pack)
        output["phase3"] = p3
    except Exception as e:
        output["phase3"] = {
            "hypothesis_valid": False,
            "confidence": 0.0,
            "position_type": "avoid",
            "suggestion": f"Phase 3 失败: {e}",
        }
        output["phase3_error"] = str(e)

    try:
        critic = hypothesis_critic_node(output)
        output["critic"] = critic
        output["critic_challenges"] = critic.get("challenges", [])
        output["critic_recommendation"] = critic.get("recommendation", "watch")
        output["adjusted_confidence"] = critic.get("adjusted_confidence", 0.5)
    except Exception as e:
        output["critic"] = {
            "challenges": [],
            "fatal_flaws": [],
            "hypothesis_survives": True,
            "adjusted_confidence": output.get("phase3", {}).get("confidence", 0.5),
            "recommendation": output.get("phase3", {}).get("position_type", "watch"),
            "review_summary": f"Critic 执行失败: {e}",
        }
        output["critic_challenges"] = []
        output["critic_recommendation"] = output["critic"]["recommendation"]
        output["adjusted_confidence"] = output["critic"]["adjusted_confidence"]
        output["critic_error"] = str(e)

    # Critic 闭环：提取 unverified major challenges，补充查询
    try:
        _run_critic_followup(output, ts_code, trade_date, stock_name, p1)
    except Exception as exc:
        log.warning("Critic 闭环异常: %s", exc)

    data_sources = set()
    data_sources.update(phase1_data.keys())
    for tc in p2.get("tool_calls_made", []):
        data_sources.add(tc.get("name", ""))
    output["data_sources"] = sorted(data_sources)

    return output
