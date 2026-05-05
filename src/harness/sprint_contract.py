"""每日 Sprint Contract — 开盘前 supervisor 与 critic 协商当日交付物。"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from llm_clients.kimi_sync import call_kimi
from llm_clients.tier_router import get_tier_config

_CONTRACT_DIR = Path("data/contracts")


class SprintContract(BaseModel):
    date: str
    stock_pool: list[str] = Field(default_factory=list, description="今日分析股票池")
    must_analyze: list[str] = Field(default_factory=list, description="必须分析的标的")
    acceptance_criteria: list[str] = Field(default_factory=list, description="验收标准")
    risk_redlines: list[str] = Field(default_factory=list, description="风险红线")


def generate_contract(
    date: str,
    handoff_summary: str = "",
    contract_dir: Path | None = None,
) -> SprintContract:
    """基于前日 handoff 生成今日 sprint contract。"""
    tier = get_tier_config("supervisor")
    prompt = (
        f"你是投资组合经理。根据以下前日情况，生成今日{date}的分析计划。\n\n"
        f"前日情况：{handoff_summary or '无'}\n\n"
        '输出 JSON：{"stock_pool":[...],"must_analyze":[...],'
        '"acceptance_criteria":[...],"risk_redlines":[...]}'
    )
    response = call_kimi(messages=[{"role": "user", "content": prompt}], **tier)
    content = response["content"]
    try:
        start = content.index("{")
        end = content.rindex("}") + 1
        data = json.loads(content[start:end])
        contract = SprintContract(date=date, **data)
    except (ValueError, json.JSONDecodeError):
        contract = SprintContract(
            date=date,
            stock_pool=[],
            must_analyze=[],
            acceptance_criteria=["完成基本分析"],
            risk_redlines=["不操作"],
        )

    d = contract_dir or _CONTRACT_DIR
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{date}.json").write_text(
        contract.model_dump_json(indent=2), encoding="utf-8"
    )
    return contract


def load_contract(
    date: str, contract_dir: Path | None = None
) -> SprintContract | None:
    d = contract_dir or _CONTRACT_DIR
    path = d / f"{date}.json"
    if not path.exists():
        return None
    return SprintContract(**json.loads(path.read_text(encoding="utf-8")))
