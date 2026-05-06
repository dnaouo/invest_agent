"""逐步运行华工科技分析，每个 agent 独立 try/except + 详细输出。"""
import sys
import json
import time
import traceback
import signal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

TS_CODE = "000988.SZ"
STOCK_NAME = "华工科技"
TRADE_DATE = "20260107"
NODE_TIMEOUT = 180  # 每个节点最多 3 分钟

state = {
    "ts_code": TS_CODE,
    "trade_date": TRADE_DATE,
    "stock_name": STOCK_NAME,
}


class NodeTimeout(Exception):
    pass


def run_node(name, func):
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
        sys.stdout.flush()
        return True
    except Exception as e:
        elapsed = time.time() - t0
        print(f"[{name}] 失败 ({elapsed:.1f}s): {e}")
        traceback.print_exc()
        sys.stdout.flush()
        return False


def main():
    print(f"华工科技（{TS_CODE}）详细分析 — 截至 {TRADE_DATE}")
    print(f"{'='*60}\n")

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
        ("1. Macro (宏观主题)", macro_node),
        ("2. Fund (基本面)", fund_node),
        ("3. Tech (技术面)", tech_node),
        ("4. Event (事件驱动)", event_node),
        ("5. Flow-Inst (机构资金)", flow_inst_node),
        ("6. Flow-Hot (游资动向)", flow_hot_node),
        ("7. Risk (风控评估)", risk_node),
        ("8. Backtest (回测分析)", backtest_node),
        ("9. Critic (独立评审)", critic_node),
        ("10. Supervisor (综合信号)", supervisor_node),
    ]

    for name, func in nodes:
        ok = run_node(name, func)
        if not ok:
            print(f"\n[WARN] {name} 失败，继续执行后续 agent...")

    print(f"\n{'='*60}")
    print("全部 agent 执行完毕。最终 state keys:", list(state.keys()))
    print(f"{'='*60}")

    output_path = Path(__file__).parent.parent / "data" / "huagong_result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n完整结果已保存: {output_path}")


if __name__ == "__main__":
    main()
