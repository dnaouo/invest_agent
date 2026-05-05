"""LangGraph 编排器 — 完整 9 agent + supervisor 编排。"""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from agents.state import MarketState
from agents.fund import fund_node
from agents.macro import macro_node
from agents.tech import tech_node
from agents.event import event_node
from agents.flow_institutional import flow_inst_node
from agents.flow_hot_money import flow_hot_node
from agents.risk import risk_node
from agents.backtest import backtest_node
from agents.critic import critic_node
from agents.supervisor import supervisor_node


def build_graph():
    """构建完整 LangGraph 图。

    Phase 1b 串行链路（可靠优先）：
    macro -> fund -> tech -> event -> flow_inst -> flow_hot
    -> risk -> backtest -> critic -> supervisor -> END
    """
    graph = StateGraph(MarketState)

    graph.add_node("macro", macro_node)
    graph.add_node("fund", fund_node)
    graph.add_node("tech", tech_node)
    graph.add_node("event", event_node)
    graph.add_node("flow_inst", flow_inst_node)
    graph.add_node("flow_hot", flow_hot_node)
    graph.add_node("risk", risk_node)
    graph.add_node("backtest", backtest_node)
    graph.add_node("critic", critic_node)
    graph.add_node("supervisor", supervisor_node)

    graph.set_entry_point("macro")
    graph.add_edge("macro", "fund")
    graph.add_edge("fund", "tech")
    graph.add_edge("tech", "event")
    graph.add_edge("event", "flow_inst")
    graph.add_edge("flow_inst", "flow_hot")
    graph.add_edge("flow_hot", "risk")
    graph.add_edge("risk", "backtest")
    graph.add_edge("backtest", "critic")
    graph.add_edge("critic", "supervisor")
    graph.add_edge("supervisor", END)

    return graph.compile()


def run_analysis(ts_code: str, trade_date: str, stock_name: str = "") -> dict:
    """运行完整分析流程。返回最终 MarketState。"""
    graph = build_graph()
    initial_state: MarketState = {
        "ts_code": ts_code,
        "trade_date": trade_date,
        "stock_name": stock_name or ts_code,
    }
    return graph.invoke(initial_state)
