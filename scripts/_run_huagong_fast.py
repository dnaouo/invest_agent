"""快速运行华工科技分析 — 关闭 thinking 模式以加速。"""
import sys
import json
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# 临时覆盖 tier_router，全部使用 B_recall（thinking=False）以加速
import llm_clients.tier_router as tr
tr.AGENT_TIER_MAP = {k: "B_recall" for k in tr.AGENT_TIER_MAP}
print(f"[INFO] 已覆盖 tier_router，全部使用 thinking=False 以加速\n")

TS_CODE = "000988.SZ"
STOCK_NAME = "华工科技"
TRADE_DATE = "20260430"

state = {
    "ts_code": TS_CODE,
    "trade_date": TRADE_DATE,
    "stock_name": STOCK_NAME,
}

results_detail = {}


def run_node(name, key, func):
    print(f"\n{'='*60}")
    print(f"[{name}] 开始执行...")
    sys.stdout.flush()
    t0 = time.time()
    try:
        result = func(state)
        elapsed = time.time() - t0
        print(f"[{name}] 完成 ({elapsed:.1f}s)")
        state.update(result)
        output = json.dumps(result, ensure_ascii=False, indent=2, default=str)
        print(output[:4000])
        if len(output) > 4000:
            print(f"  ... (输出截断，总长 {len(output)} 字符)")
        results_detail[key] = {"status": "ok", "elapsed": elapsed, "data": result}
        sys.stdout.flush()
        return True
    except Exception as e:
        elapsed = time.time() - t0
        print(f"[{name}] 失败 ({elapsed:.1f}s): {e}")
        traceback.print_exc()
        results_detail[key] = {"status": "error", "elapsed": elapsed, "error": str(e)}
        sys.stdout.flush()
        return False


def main():
    print(f"华工科技（{TS_CODE}）详细分析 — 截至 {TRADE_DATE}")
    print(f"{'='*60}")
    sys.stdout.flush()

    from agents.macro import macro_node
    from agents.fund import fund_node
    from agents.tech import tech_node
    from agents.event import event_node
    from agents.flow_institutional import flow_inst_node
    from agents.flow_hot_money import flow_hot_node
    from agents.risk import risk_node
    from agents.backtest import backtest_node
    from agents.critic import critic_node
    from agents.supervisor import supervisor_node

    nodes = [
        ("1. Macro (宏观主题)", "macro_themes", macro_node),
        ("2. Fund (基本面)", "fundamental_score", fund_node),
        ("3. Tech (技术面)", "technical_score", tech_node),
        ("4. Event (事件驱动)", "event_analysis", event_node),
        ("5. Flow-Inst (机构资金)", "flow_institutional", flow_inst_node),
        ("6. Flow-Hot (游资动向)", "flow_hot_money", flow_hot_node),
        ("7. Risk (风控评估)", "risk_assessment", risk_node),
        ("8. Backtest (回测分析)", "backtest_result", backtest_node),
        ("9. Critic (独立评审)", "critic_review", critic_node),
        ("10. Supervisor (综合信号)", "supervisor_signal", supervisor_node),
    ]

    total_t0 = time.time()
    for name, key, func in nodes:
        run_node(name, key, func)

    total_elapsed = time.time() - total_t0

    print(f"\n{'='*60}")
    print(f"全部 agent 执行完毕 (总耗时 {total_elapsed:.1f}s)")
    print(f"{'='*60}")

    print(f"\n--- 各 Agent 评分汇总 ---")
    for key in ["macro_themes", "fundamental_score", "technical_score",
                "event_analysis", "flow_institutional", "flow_hot_money",
                "risk_assessment", "backtest_result"]:
        score = state.get(key, {}).get("score", "N/A")
        elapsed = results_detail.get(key, {}).get("elapsed", 0)
        status = results_detail.get(key, {}).get("status", "?")
        print(f"  {key}: score={score}, status={status}, time={elapsed:.1f}s")

    critic = state.get("critic_review", {})
    print(f"\n--- Critic ---")
    print(f"  Score: {critic.get('score', 'N/A')}")
    print(f"  Verdict: {critic.get('verdict', 'N/A')}")

    signal = state.get("supervisor_signal", {})
    print(f"\n--- Supervisor Signal ---")
    print(f"  Direction: {signal.get('direction', 'N/A')}")
    print(f"  Confidence: {signal.get('confidence', 'N/A')}")
    print(f"  Position: {signal.get('position_pct', 'N/A')}%")
    sys.stdout.flush()

    output_path = Path(__file__).parent.parent / "data" / "huagong_result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n完整结果已保存: {output_path}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
