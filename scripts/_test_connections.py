"""测试数据源和 LLM 连接。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

def test_tushare():
    print("1. Testing tushare...")
    t0 = time.time()
    from sandboxes.data import tushare_client
    r = tushare_client.get_daily(ts_code="000988.SZ", start_date="20260101", end_date="20260107")
    print(f"   status={r['status']}, records={len(r.get('data',[]))}, time={time.time()-t0:.1f}s")
    return r["status"] == "ok"

def test_akshare():
    print("2. Testing akshare (cls_news)...")
    t0 = time.time()
    from sandboxes.data import akshare_client
    r = akshare_client.get_cls_news(count=5)
    print(f"   status={r['status']}, records={len(r.get('data',[]))}, time={time.time()-t0:.1f}s")
    if r["status"] == "error":
        print(f"   error: {r.get('message','')[:200]}")
    return r["status"] == "ok"

def test_akshare_jin10():
    print("3. Testing akshare (jin10)...")
    t0 = time.time()
    from sandboxes.data import akshare_client
    r = akshare_client.get_jin10_news(count=5)
    print(f"   status={r['status']}, records={len(r.get('data',[]))}, time={time.time()-t0:.1f}s")
    if r["status"] == "error":
        print(f"   error: {r.get('message','')[:200]}")
    return r["status"] == "ok"

def test_kimi():
    print("4. Testing Kimi API...")
    t0 = time.time()
    from llm_clients.kimi_sync import call_kimi
    r = call_kimi("hello, respond with just 'ok'", max_tokens=32)
    print(f"   content={r['content'][:100]}, time={time.time()-t0:.1f}s")
    return True

if __name__ == "__main__":
    for fn in [test_tushare, test_akshare, test_akshare_jin10, test_kimi]:
        try:
            fn()
        except Exception as e:
            print(f"   FAILED: {e}")
        print()
