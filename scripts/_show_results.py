"""打印已完成股票的 10 agent 详细结果。"""
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

AGENT_KEYS = [
    ("macro_themes", "宏观主题"),
    ("fundamental_score", "基本面"),
    ("technical_score", "技术面"),
    ("event_analysis", "事件驱动"),
    ("flow_institutional", "机构资金"),
    ("flow_hot_money", "游资跟踪"),
    ("risk_assessment", "风险评估"),
    ("backtest_result", "回测验证"),
    ("critic_review", "Critic审查"),
    ("supervisor_signal", "Supervisor信号"),
]

d = json.load(open("data/batch_result_20260506.json", "r", encoding="utf-8"))

for ts_code, detail in d["details"].items():
    name = next((s["stock_name"] for s in d["summary"] if s["ts_code"] == ts_code), ts_code)
    elapsed = next((s["elapsed"] for s in d["summary"] if s["ts_code"] == ts_code), "?")
    print(f"\n{'='*60}")
    print(f"  {name}（{ts_code}）  耗时: {elapsed}s")
    print(f"{'='*60}")

    for k, label in AGENT_KEYS:
        a = detail.get(k, {})
        score = a.get("score", "-")
        summary = a.get("summary", "")
        if not summary:
            for fb in ("direction", "verdict", "worst_case"):
                if fb in a:
                    summary = f"{fb}={a[fb]}"
                    break
        print(f"\n  [{label}] 评分: {score}")
        print(f"    {summary}")
        highlights = a.get("highlights", a.get("reasons", []))
        risks = a.get("risks", a.get("objections", []))
        for h in highlights[:3]:
            print(f"    + {h}")
        for r in risks[:3]:
            print(f"    - {r}")

    sig = detail.get("supervisor_signal", {})
    print(f"\n  >>> 最终信号: {sig.get('direction','?')}  置信度: {sig.get('confidence','?')}  仓位: {sig.get('position_pct','?')}%  止损: {sig.get('stop_loss','?')}")
    print()
