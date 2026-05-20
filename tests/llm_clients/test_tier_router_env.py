import os
from unittest.mock import patch
from llm_clients import tier_router


def test_default_uses_agent_tier_map():
    cfg = tier_router.get_tier_config("hypothesis_verify")
    assert "thinking" in cfg and "max_tokens" in cfg


def test_kimi_thinking_level_off_disables_all():
    with patch.dict(os.environ, {"KIMI_THINKING_LEVEL": "off"}):
        for agent in ["hypothesis_verify", "hypothesis_critic", "supervisor"]:
            cfg = tier_router.get_tier_config(agent)
            assert cfg["thinking"] is False, f"{agent} should be off"


def test_kimi_thinking_level_lite_only_critical_phases():
    with patch.dict(os.environ, {"KIMI_THINKING_LEVEL": "lite"}):
        # lite: 只有 verify/judge/critic/memo_writer 开 thinking
        assert tier_router.get_tier_config("hypothesis_verify")["thinking"] is True
        assert tier_router.get_tier_config("hypothesis_judge")["thinking"] is True
        assert tier_router.get_tier_config("hypothesis_critic")["thinking"] is True
        # 其他 agent 不开
        assert tier_router.get_tier_config("hypothesis_scan")["thinking"] is False
        assert tier_router.get_tier_config("flow_hot")["thinking"] is False


def test_kimi_thinking_level_full_uses_default_map():
    with patch.dict(os.environ, {"KIMI_THINKING_LEVEL": "full"}):
        # full = 不覆盖，按 AGENT_TIER_MAP
        assert tier_router.get_tier_config("supervisor")["thinking"] is True
