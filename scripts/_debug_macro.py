"""调试 Macro agent：分步测量数据拉取和 LLM 调用。"""
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

TRADE_DATE = "20260107"

print("=== Macro Agent 分步调试 ===\n")

print("Step 1: get_ths_index...")
sys.stdout.flush()
t0 = time.time()
from sandboxes.data import tushare_client
r = tushare_client.get_ths_index()
print(f"  status={r['status']}, records={len(r.get('data',[]))}, time={time.time()-t0:.1f}s")
sys.stdout.flush()

print("\nStep 2: get_cls_news...")
sys.stdout.flush()
t0 = time.time()
from sandboxes.data import akshare_client
r2 = akshare_client.get_cls_news(count=50)
print(f"  status={r2['status']}, records={len(r2.get('data',[]))}, time={time.time()-t0:.1f}s")
sys.stdout.flush()

print("\nStep 3: get_jin10_news...")
sys.stdout.flush()
t0 = time.time()
r3 = akshare_client.get_jin10_news(count=50)
print(f"  status={r3['status']}, records={len(r3.get('data',[]))}, time={time.time()-t0:.1f}s")
sys.stdout.flush()

data = {}
if r["status"] == "ok":
    data["ths_index"] = r["data"][:30]
if r2["status"] == "ok":
    data["cls_news"] = r2["data"][:20]
if r3["status"] == "ok":
    data["jin10_news"] = r3["data"][:20]

data_str = json.dumps(data, ensure_ascii=False, default=str)
print(f"\nTotal data payload size: {len(data_str)} chars")
sys.stdout.flush()

print("\nStep 4: Calling Kimi API...")
sys.stdout.flush()
t0 = time.time()

from llm_clients.kimi_sync import call_kimi
from llm_clients.tier_router import get_tier_config

prompt_path = Path(__file__).resolve().parent.parent / "src" / "agents" / "prompts" / "macro.md"
system_prompt = prompt_path.read_text(encoding="utf-8")

user_message = (
    f"请分析截至 {TRADE_DATE} 的宏观主题格局。\n\n"
    f"以下是数据：\n{data_str}"
)

tier = get_tier_config("macro")
print(f"  tier config: {tier}")
print(f"  system_prompt length: {len(system_prompt)}")
print(f"  user_message length: {len(user_message)}")
sys.stdout.flush()

response = call_kimi(
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ],
    **tier,
)
print(f"  Kimi responded in {time.time()-t0:.1f}s")
print(f"  content length: {len(response.get('content',''))}")
print(f"  content preview: {response.get('content','')[:500]}")
sys.stdout.flush()
