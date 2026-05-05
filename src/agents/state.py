"""LangGraph 共享状态定义 + 信号输出 schema。"""
from __future__ import annotations

from typing import Literal

from typing_extensions import TypedDict
from pydantic import BaseModel, Field


class MarketState(TypedDict, total=False):
    """LangGraph 图的共享状态。每个 agent 节点读写自己的 key。"""

    trade_date: str
    ts_code: str
    stock_name: str
    fundamental_score: dict
    technical_score: dict
    macro_themes: dict
    event_analysis: dict
    flow_institutional: dict
    flow_hot_money: dict
    risk_assessment: dict
    backtest_result: dict
    critic_review: dict
    supervisor_signal: dict


class AgentOutput(BaseModel):
    """单个 agent 的标准化输出。"""

    score: float = Field(ge=0, le=100, description="评分 0-100")
    highlights: list[str] = Field(default_factory=list, description="积极因素")
    risks: list[str] = Field(default_factory=list, description="风险因素")
    data_sources: list[str] = Field(default_factory=list, description="引用的数据来源")
    summary: str = Field(default="", description="一段话总结")


class CriticOutput(BaseModel):
    """Critic Agent 的输出。"""

    score: float = Field(ge=0, le=100, description="评分 0-100")
    objections: list[str] = Field(default_factory=list, description="反对意见")
    worst_case: str = Field(default="", description="最坏情况描述")
    verdict: Literal["pass", "reject"] = Field(description="通过或拒绝")


class SignalOutput(BaseModel):
    """最终投资信号输出。"""

    ts_code: str
    stock_name: str = ""
    direction: Literal["buy", "sell", "hold"]
    confidence: float = Field(ge=0, le=1, description="置信度 0-1")
    position_pct: float = Field(ge=0, le=15, description="建议仓位百分比")
    stop_loss: float = Field(ge=0, description="止损价")
    reasons: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    critic_score: float = Field(ge=0, le=100, description="Critic 评分")
    critic_objections: list[str] = Field(default_factory=list)
