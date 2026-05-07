"""合并两份批量结果并输出完整 11 只详细报告。"""
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

d1 = json.load(open("data/batch_result_20260506.json", "r", encoding="utf-8"))
d2 = json.load(open("data/batch_retry_20260506.json", "r", encoding="utf-8"))

all_summary = [s for s in d1["summary"] if s["status"] == "ok"]
all_summary.extend(d2["summary"])
all_details = {**d1["details"], **d2["details"]}

merged = {
    "trade_date": "20260506",
    "total_stocks": len(all_summary),
    "completed": len(all_summary),
    "summary": all_summary,
    "details": all_details,
}
with open("data/batch_all_20260506.json", "w", encoding="utf-8") as f:
    json.dump(merged, f, ensure_ascii=False, indent=2, default=str)

# 汇总表
print(f"\n{'='*90}")
print(f"  11 只股票分析汇总（2026-05-06）")
print(f"{'='*90}")
print(f"{'股票':<10} {'基本':>4} {'技术':>4} {'事件':>4} {'机构':>4} {'游资':>4} {'风险':>4} {'回测':>4} {'Critic':>7} {'信号':<5} {'置信':>4} {'仓位':>4}")
print("-" * 90)

for s in all_summary:
    ts = s["ts_code"]
    det = all_details.get(ts, {})
    name = s["stock_name"]
    fund = det.get("fundamental_score", {}).get("score", "-")
    tech = det.get("technical_score", {}).get("score", "-")
    evt = det.get("event_analysis", {}).get("score", "-")
    inst = det.get("flow_institutional", {}).get("score", "-")
    hot = det.get("flow_hot_money", {}).get("score", "-")
    risk = det.get("risk_assessment", {}).get("score", "-")
    bt = det.get("backtest_result", {}).get("score", "-")
    cr = det.get("critic_review", {})
    cr_score = cr.get("score", "-")
    cr_v = cr.get("verdict", "?")
    sig = det.get("supervisor_signal", {})
    direction = sig.get("direction", "?")
    conf = sig.get("confidence", "?")
    pos = sig.get("position_pct", "?")
    print(f"{name:<10} {fund:>4} {tech:>4} {evt:>4} {inst:>4} {hot:>4} {risk:>4} {bt:>4} {cr_score:>3}/{cr_v:<4} {direction:<5} {conf:>4} {pos:>4}%")

print(f"\n{'='*90}\n")

# 详细报告
for s in all_summary:
    ts = s["ts_code"]
    det = all_details.get(ts, {})
    name = s["stock_name"]
    elapsed = s.get("elapsed", "?")
    print(f"\n{'='*60}")
    print(f"  {name}（{ts}）  耗时: {elapsed}s")
    print(f"{'='*60}")
    for k, label in AGENT_KEYS:
        a = det.get(k, {})
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
    sig = det.get("supervisor_signal", {})
    print(f"\n  >>> 最终信号: {sig.get('direction','?')}  置信度: {sig.get('confidence','?')}  仓位: {sig.get('position_pct','?')}%  止损: {sig.get('stop_loss','?')}")
    print()
