"""Tests for harness.hypothesis_engine — 假设驱动分析引擎。"""
from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest


_PHASE1_JSON = json.dumps({
    "hypothesis": "云南锗业正从传统锗业向化合物半导体材料转型",
    "questions": [
        "化合物半导体营收增速是否持续加速？",
        "InP 衬底行业供需格局如何？",
        "锗价波动对利润的影响？",
    ],
    "stock_type": "industry_logic",
})

_PHASE2_JSON = json.dumps({
    "verifications": [
        {"question": "化合物半导体营收增速是否持续加速？", "verdict": "supported", "evidence": "营收从0到1.38亿", "data_sources": ["search_reports"]},
        {"question": "InP 衬底行业供需格局如何？", "verdict": "supported", "evidence": "供不应求", "data_sources": ["search_news"]},
        {"question": "锗价波动对利润的影响？", "verdict": "inconclusive", "evidence": "近期稳定", "data_sources": ["search_news"]},
    ],
})

_PHASE3_JSON = json.dumps({
    "hypothesis": "云南锗业正从传统锗业向化合物半导体材料转型",
    "hypothesis_valid": True,
    "confidence": 0.65,
    "evidence_for": ["营收从0到1.38亿"],
    "evidence_against": ["扣非净利润亏损"],
    "key_risks": ["锗价波动"],
    "catalyst": "Q2 财报",
    "suggestion": "观察",
    "position_type": "watch",
})

_FINA_OK = {"status": "ok", "data": [{"roe": 5.2, "grossprofit_margin": 30.0}]}
_DAILY_BASIC_OK = {"status": "ok", "data": [{"pe_ttm": 742.0, "pb": 5.5, "total_mv": 100.0}]}
_THS_INDEX_OK = {"status": "ok", "data": []}
_MAINBZ_OK = {"status": "ok", "data": [{"bz_item": "锗产品"}, {"bz_item": "化合物半导体材料"}]}
_NEWS_RESULT = {"ts_code": "002428.SZ", "keywords_used": ["锗"], "news_count": 0, "news": [], "summary": "近7天无相关快讯"}

_CRITIC_RESULT = {
    "challenges": [
        {"dimension": "假设前提", "challenge": "测试挑战", "severity": "medium", "unverified": True},
    ],
    "fatal_flaws": [],
    "hypothesis_survives": True,
    "adjusted_confidence": 0.55,
    "recommendation": "watch",
    "review_summary": "测试审查通过",
}


@pytest.fixture(autouse=True)
def _patch_tushare():
    import harness.hypothesis_engine as mod
    with patch.object(mod, "tushare_client") as mock_ts, \
         patch.object(mod, "search_news_for_stock", return_value=_NEWS_RESULT), \
         patch.object(mod, "extract_mainbz_keywords", return_value=["锗", "化合物半导体"]):
        mock_ts.get_fina_indicator.return_value = _FINA_OK
        mock_ts.get_daily_basic.return_value = _DAILY_BASIC_OK
        mock_ts.get_ths_index.return_value = _THS_INDEX_OK
        mock_ts.get_fina_mainbz.return_value = _MAINBZ_OK
        yield mock_ts


class TestFetchPhase1Data:
    def test_returns_fina_and_daily_basic(self, _patch_tushare):
        from harness.hypothesis_engine import _fetch_phase1_data

        data = _fetch_phase1_data("002428.SZ", "20260402")
        assert "fina_indicator" in data
        assert data["fina_indicator"]["roe"] == 5.2
        assert "daily_basic" in data
        assert data["daily_basic"]["pe_ttm"] == 742.0

    def test_handles_api_failure(self, _patch_tushare):
        from harness.hypothesis_engine import _fetch_phase1_data

        _patch_tushare.get_fina_indicator.side_effect = Exception("API down")
        _patch_tushare.get_daily_basic.side_effect = Exception("API down")
        _patch_tushare.get_ths_index.side_effect = Exception("API down")

        data = _fetch_phase1_data("002428.SZ", "20260402")
        assert isinstance(data, dict)


class TestExtractJson:
    def test_extracts_json_from_mixed_text(self):
        from harness.hypothesis_engine import _extract_json

        text = '下面是分析结果：\n{"key": "value"}\n以上。'
        result = _extract_json(text)
        assert result == {"key": "value"}

    def test_returns_none_for_invalid(self):
        from harness.hypothesis_engine import _extract_json

        assert _extract_json("no json here") is None

    def test_returns_none_for_empty(self):
        from harness.hypothesis_engine import _extract_json

        assert _extract_json("") is None

    def test_extracts_from_code_fence(self):
        from harness.hypothesis_engine import _extract_json

        text = '分析如下：\n```json\n{"verifications": [{"q": "test"}]}\n```\n结束'
        result = _extract_json(text)
        assert result == {"verifications": [{"q": "test"}]}

    def test_extracts_from_code_fence_no_lang(self):
        from harness.hypothesis_engine import _extract_json

        text = '```\n{"hypothesis": "test"}\n```'
        result = _extract_json(text)
        assert result == {"hypothesis": "test"}

    def test_handles_nested_json(self):
        from harness.hypothesis_engine import _extract_json

        text = '说明：{"verifications": [{"question": "Q1", "verdict": "supported"}]} 以上'
        result = _extract_json(text)
        assert result is not None
        assert "verifications" in result


class TestRunPhase1:
    def test_happy_path(self):
        import harness.hypothesis_engine as mod
        with patch.object(mod, "call_kimi", return_value={"content": _PHASE1_JSON}):
            result = mod._run_phase1(
                "002428.SZ", "20260402", "云南锗业", "涨停", {"fina_indicator": {}}
            )
        assert result["hypothesis"] == "云南锗业正从传统锗业向化合物半导体材料转型"
        assert len(result["questions"]) == 3
        assert result["stock_type"] == "industry_logic"

    def test_fallback_on_bad_json(self):
        import harness.hypothesis_engine as mod
        with patch.object(mod, "call_kimi", return_value={"content": "这是一段非JSON文本"}):
            result = mod._run_phase1(
                "002428.SZ", "20260402", "云南锗业", "涨停", {}
            )
        assert "hypothesis" in result
        assert len(result["questions"]) == 3
        assert result["stock_type"] == "industry_logic"

    def test_fills_missing_keys(self):
        import harness.hypothesis_engine as mod
        with patch.object(mod, "call_kimi", return_value={"content": json.dumps({"hypothesis": "test"})}):
            result = mod._run_phase1(
                "002428.SZ", "20260402", "云南锗业", "涨停", {}
            )
        assert "questions" in result
        assert "stock_type" in result


class TestRunPhase2:
    def test_happy_path(self):
        import harness.hypothesis_engine as mod
        mock_return = {
            "content": _PHASE2_JSON,
            "reasoning_content": None,
            "tool_calls_made": [{"name": "search_reports", "args": {}, "result": "ok"}],
        }
        with patch.object(mod, "run_agent_with_tools", return_value=mock_return):
            p1 = json.loads(_PHASE1_JSON)
            result = mod._run_phase2("002428.SZ", "20260402", "云南锗业", p1)
        assert len(result["verifications"]) == 3
        assert result["verifications"][0]["verdict"] == "supported"
        assert len(result["tool_calls_made"]) == 1

    def test_fallback_on_bad_json(self):
        import harness.hypothesis_engine as mod
        mock_return = {
            "content": "无法解析",
            "reasoning_content": None,
            "tool_calls_made": [],
        }
        with patch.object(mod, "run_agent_with_tools", return_value=mock_return):
            p1 = json.loads(_PHASE1_JSON)
            result = mod._run_phase2("002428.SZ", "20260402", "云南锗业", p1)
        assert len(result["verifications"]) == 3
        for v in result["verifications"]:
            assert v["verdict"] == "inconclusive"

    def test_uses_all_tools(self):
        import harness.hypothesis_engine as mod
        mock_return = {
            "content": _PHASE2_JSON,
            "reasoning_content": None,
            "tool_calls_made": [],
        }
        with patch.object(mod, "run_agent_with_tools", return_value=mock_return) as mock_rat:
            p1 = json.loads(_PHASE1_JSON)
            mod._run_phase2("002428.SZ", "20260402", "云南锗业", p1)
            call_args = mock_rat.call_args
            assert call_args.kwargs["tools"] is mod.ALL_TOOLS

    def test_fallback_llm_structure_on_bad_json(self):
        """当 run_agent_with_tools 返回非 JSON content 但有 tool_calls_made 时，
        应通过 LLM 结构化获取 verifications。"""
        import harness.hypothesis_engine as mod
        mock_return = {
            "content": "我分析了以下数据...\nInP 产能 45 万片\n投资 18856 万元",
            "reasoning_content": None,
            "tool_calls_made": [
                {"name": "search_knowledge", "args": {"query": "InP"}, "result": "产能45万片，投资18856万元"},
            ],
        }
        structured = json.dumps({
            "verifications": [
                {"question": "Q1", "verdict": "supported", "evidence": "投资18856万", "data_sources": ["search_knowledge"]},
                {"question": "Q2", "verdict": "supported", "evidence": "产能45万片", "data_sources": ["search_knowledge"]},
                {"question": "Q3", "verdict": "inconclusive", "evidence": "无数据", "data_sources": []},
            ],
        })
        with patch.object(mod, "run_agent_with_tools", return_value=mock_return), \
             patch.object(mod, "call_kimi", return_value={"content": structured}):
            p1 = json.loads(_PHASE1_JSON)
            result = mod._run_phase2("002428.SZ", "20260402", "云南锗业", p1)
        assert len(result["verifications"]) == 3
        assert result["verifications"][0]["verdict"] == "supported"

    def test_fallback_raw_evidence_when_all_fails(self):
        """当 JSON 解析和 LLM 结构化都失败时，应保留 raw_tool_evidence。"""
        import harness.hypothesis_engine as mod
        mock_return = {
            "content": "分析完成但无法输出JSON",
            "reasoning_content": None,
            "tool_calls_made": [
                {"name": "search_reports", "args": {"keyword": "锗"}, "result": "中银证券研报摘要..."},
            ],
        }
        with patch.object(mod, "run_agent_with_tools", return_value=mock_return), \
             patch.object(mod, "call_kimi", return_value={"content": "无法结构化"}):
            p1 = json.loads(_PHASE1_JSON)
            result = mod._run_phase2("002428.SZ", "20260402", "云南锗业", p1)
        assert "raw_tool_evidence" in result
        assert "中银证券" in result["raw_tool_evidence"]
        assert len(result["tool_calls_made"]) == 1


class TestRunPhase3:
    def test_happy_path(self):
        import harness.hypothesis_engine as mod
        with patch.object(mod, "call_kimi", return_value={"content": _PHASE3_JSON}):
            p1 = json.loads(_PHASE1_JSON)
            p2 = json.loads(_PHASE2_JSON)
            result = mod._run_phase3("002428.SZ", "云南锗业", p1, p2, {"daily_basic": {"pe_ttm": 742}})
        assert result["hypothesis_valid"] is True
        assert result["confidence"] == 0.65
        assert result["position_type"] == "watch"

    def test_fallback_on_bad_json(self):
        import harness.hypothesis_engine as mod
        with patch.object(mod, "call_kimi", return_value={"content": "无法判断"}):
            p1 = json.loads(_PHASE1_JSON)
            result = mod._run_phase3("002428.SZ", "云南锗业", p1, {"verifications": []}, {})
        assert result["hypothesis_valid"] is False
        assert result["position_type"] == "avoid"

    def test_fills_missing_keys(self):
        import harness.hypothesis_engine as mod
        with patch.object(mod, "call_kimi", return_value={"content": json.dumps({"hypothesis_valid": True, "confidence": 0.8})}):
            p1 = json.loads(_PHASE1_JSON)
            result = mod._run_phase3("002428.SZ", "云南锗业", p1, {"verifications": []}, {})
        assert "position_type" in result
        assert "key_risks" in result
        assert "evidence_for" in result


class TestRunHypothesisAnalysis:
    def test_end_to_end(self):
        import harness.hypothesis_engine as mod
        with patch.object(mod, "call_kimi") as mock_kimi, \
             patch.object(mod, "run_agent_with_tools") as mock_rat, \
             patch.object(mod, "hypothesis_critic_node", return_value=_CRITIC_RESULT):
            mock_kimi.side_effect = [
                {"content": _PHASE1_JSON},
                {"content": _PHASE3_JSON},
            ]
            mock_rat.return_value = {
                "content": _PHASE2_JSON,
                "reasoning_content": None,
                "tool_calls_made": [{"name": "search_reports", "args": {}, "result": ""}],
            }

            result = mod.run_hypothesis_analysis(
                ts_code="002428.SZ",
                trade_date="20260402",
                stock_name="云南锗业",
                trigger_reason="化合物半导体板块涨停",
            )

        assert result["ts_code"] == "002428.SZ"
        assert "phase1" in result
        assert "phase2" in result
        assert "phase3" in result
        assert "critic" in result
        assert result["phase3"]["hypothesis_valid"] is True
        assert result["phase3"]["position_type"] == "watch"
        assert result["critic"]["hypothesis_survives"] is True
        assert "critic_challenges" in result
        assert "critic_recommendation" in result
        assert "adjusted_confidence" in result
        assert "data_sources" in result

    def test_phase1_failure_short_circuits(self):
        import harness.hypothesis_engine as mod
        with patch.object(mod, "call_kimi", side_effect=Exception("Kimi API down")):
            result = mod.run_hypothesis_analysis(
                ts_code="002428.SZ",
                trade_date="20260402",
                stock_name="云南锗业",
                trigger_reason="涨停",
            )

        assert "phase1_error" in result
        assert result["phase3"]["position_type"] == "avoid"

    def test_phase2_failure_continues(self):
        import harness.hypothesis_engine as mod
        with patch.object(mod, "call_kimi") as mock_kimi, \
             patch.object(mod, "run_agent_with_tools", side_effect=Exception("Tool executor down")), \
             patch.object(mod, "hypothesis_critic_node", return_value=_CRITIC_RESULT):
            mock_kimi.side_effect = [
                {"content": _PHASE1_JSON},
                {"content": _PHASE3_JSON},
            ]

            result = mod.run_hypothesis_analysis(
                ts_code="002428.SZ",
                trade_date="20260402",
                stock_name="云南锗业",
                trigger_reason="涨停",
            )

        assert "phase2_error" in result
        assert "phase3" in result
        assert "critic" in result

    def test_data_sources_aggregated(self):
        import harness.hypothesis_engine as mod
        with patch.object(mod, "call_kimi") as mock_kimi, \
             patch.object(mod, "run_agent_with_tools") as mock_rat, \
             patch.object(mod, "hypothesis_critic_node", return_value=_CRITIC_RESULT):
            mock_kimi.side_effect = [
                {"content": _PHASE1_JSON},
                {"content": _PHASE3_JSON},
            ]
            mock_rat.return_value = {
                "content": _PHASE2_JSON,
                "reasoning_content": None,
                "tool_calls_made": [
                    {"name": "search_reports", "args": {}, "result": ""},
                    {"name": "search_news", "args": {}, "result": ""},
                ],
            }

            result = mod.run_hypothesis_analysis(
                ts_code="002428.SZ",
                trade_date="20260402",
                stock_name="云南锗业",
                trigger_reason="涨停",
            )

        ds = result["data_sources"]
        assert "search_reports" in ds
        assert "search_news" in ds
        assert "fina_indicator" in ds
        assert "daily_basic" in ds

    def test_critic_failure_does_not_crash(self):
        """Phase 4 Critic 失败时不应影响整体流程。"""
        import harness.hypothesis_engine as mod
        with patch.object(mod, "call_kimi") as mock_kimi, \
             patch.object(mod, "run_agent_with_tools") as mock_rat, \
             patch.object(mod, "hypothesis_critic_node", side_effect=Exception("Critic down")):
            mock_kimi.side_effect = [
                {"content": _PHASE1_JSON},
                {"content": _PHASE3_JSON},
            ]
            mock_rat.return_value = {
                "content": _PHASE2_JSON,
                "reasoning_content": None,
                "tool_calls_made": [],
            }

            result = mod.run_hypothesis_analysis(
                ts_code="002428.SZ",
                trade_date="20260402",
                stock_name="云南锗业",
                trigger_reason="涨停",
            )

        assert "critic_error" in result
        assert result["critic"]["hypothesis_survives"] is True
        assert result["critic_recommendation"] == "watch"
