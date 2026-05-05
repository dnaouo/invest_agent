"""Tests for harness.sprint_contract module."""
from __future__ import annotations

import json
from unittest.mock import patch

from harness.sprint_contract import SprintContract, generate_contract, load_contract


_MOCK_JSON_RESPONSE = json.dumps({
    "stock_pool": ["000001.SZ", "600519.SH"],
    "must_analyze": ["600519.SH"],
    "acceptance_criteria": ["完成基本面分析", "风险评估到位"],
    "risk_redlines": ["单日回撤不超过5%"],
})


class TestGenerateContract:
    def test_generate_contract(self, tmp_path):
        with patch("harness.sprint_contract.call_kimi") as mock_kimi, \
             patch("harness.sprint_contract.get_tier_config") as mock_tier:
            mock_kimi.return_value = {"content": _MOCK_JSON_RESPONSE}
            mock_tier.return_value = {"thinking": True, "max_tokens": 32768}

            contract = generate_contract("2026-05-03", contract_dir=tmp_path)

        assert isinstance(contract, SprintContract)
        assert contract.date == "2026-05-03"
        assert contract.stock_pool == ["000001.SZ", "600519.SH"]
        assert contract.must_analyze == ["600519.SH"]
        assert len(contract.acceptance_criteria) == 2
        assert len(contract.risk_redlines) == 1

        saved = tmp_path / "2026-05-03.json"
        assert saved.exists()
        data = json.loads(saved.read_text(encoding="utf-8"))
        assert data["date"] == "2026-05-03"

    def test_generate_contract_parse_failure(self, tmp_path):
        with patch("harness.sprint_contract.call_kimi") as mock_kimi, \
             patch("harness.sprint_contract.get_tier_config") as mock_tier:
            mock_kimi.return_value = {"content": "这不是 JSON，无法解析。"}
            mock_tier.return_value = {"thinking": True, "max_tokens": 32768}

            contract = generate_contract("2026-05-03", contract_dir=tmp_path)

        assert isinstance(contract, SprintContract)
        assert contract.date == "2026-05-03"
        assert contract.stock_pool == []
        assert contract.must_analyze == []
        assert contract.acceptance_criteria == ["完成基本分析"]
        assert contract.risk_redlines == ["不操作"]

        saved = tmp_path / "2026-05-03.json"
        assert saved.exists()


class TestLoadContract:
    def test_load_contract(self, tmp_path):
        contract = SprintContract(
            date="2026-05-02",
            stock_pool=["000858.SZ"],
            must_analyze=["000858.SZ"],
            acceptance_criteria=["完成技术面分析"],
            risk_redlines=["不追高"],
        )
        (tmp_path / "2026-05-02.json").write_text(
            contract.model_dump_json(indent=2), encoding="utf-8"
        )

        loaded = load_contract("2026-05-02", contract_dir=tmp_path)
        assert loaded is not None
        assert loaded.date == "2026-05-02"
        assert loaded.stock_pool == ["000858.SZ"]
        assert loaded.must_analyze == ["000858.SZ"]

    def test_load_nonexistent(self, tmp_path):
        result = load_contract("1999-01-01", contract_dir=tmp_path)
        assert result is None
