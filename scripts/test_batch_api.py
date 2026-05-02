"""Kimi Batch API 真实调用验证脚本。提交 1 条最简请求，验证全流程。"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from llm_clients.kimi_batch import submit_batch, check_batch, retrieve_batch


def main():
    print("=== Kimi Batch API 真实调用验证 ===\n")

    requests = [
        {
            "custom_id": "test_001",
            "body": {
                "model": "kimi-k2.6",
                "messages": [{"role": "user", "content": "用一句话介绍 A 股市场"}],
                "max_tokens": 256,
            },
        }
    ]

    print("[1/3] 提交 batch...")
    batch_id = submit_batch(requests, job_name="test_batch_api")
    print(f"  batch_id: {batch_id}")

    print("\n[2/3] 等待完成（轮询，最多 10 分钟）...")
    for i in range(60):
        status = check_batch(batch_id)
        state = status.get("status", "unknown")
        print(f"  [{i*10}s] status: {state}")
        if state == "completed":
            break
        if state in ("failed", "cancelled", "expired"):
            print(f"  [FAIL] batch 失败: {status}")
            return
        time.sleep(10)
    else:
        print("  [TIMEOUT] 超过 10 分钟未完成")
        return

    print("\n[3/3] 拉取结果...")
    results = retrieve_batch(batch_id, job_name="test_batch_api")
    for r in results:
        print(f"  custom_id: {r.get('custom_id')}")
        resp = r.get("response", {})
        body = resp.get("body", {})
        choices = body.get("choices", [])
        if choices:
            print(f"  content: {choices[0].get('message', {}).get('content', '')[:200]}")

    print("\n[DONE] Batch API 验证完成")


if __name__ == "__main__":
    main()
