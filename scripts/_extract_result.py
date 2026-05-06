"""从终端输出文件中提取完整分析结果。"""
import json
import re

TERMINAL_FILE = r"C:\Users\18401\.cursor\projects\d-a-stock-agent\terminals\771407.txt"
OUTPUT_FILE = r"D:\a_stock_agent\data\huagong_result.json"

with open(TERMINAL_FILE, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

state = {"ts_code": "000988.SZ", "trade_date": "20260430", "stock_name": "华工科技"}

blocks = re.findall(r"(\{[\s\S]*?\n\})", content)
for block in blocks:
    try:
        d = json.loads(block)
        state.update(d)
    except (json.JSONDecodeError, ValueError):
        pass

print("Keys:", list(state.keys()))
for k in [
    "macro_themes", "fundamental_score", "technical_score",
    "event_analysis", "flow_institutional", "flow_hot_money",
    "risk_assessment", "backtest_result", "critic_review", "supervisor_signal",
]:
    v = state.get(k, {})
    score = v.get("score", "N/A")
    print(f"  {k}: score={score}")

sv = state.get("supervisor_signal", {})
print(f"\nSupervisor: direction={sv.get('direction')}, confidence={sv.get('confidence')}, position={sv.get('position_pct')}%")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=2, default=str)
print(f"\nSaved to {OUTPUT_FILE}")
