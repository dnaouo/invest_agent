"""Kimi K2.6 Batch API 客户端 — Tier C/D 批量调用（60% 价格 + 24h 完成窗口）。"""

from __future__ import annotations

import json
from pathlib import Path

from openai import OpenAI

from vault.proxy import get_credential

_BASE_URL = "https://api.moonshot.cn/v1"
_BATCH_DIR = Path("data/batch_jobs")
_MAX_LINES = 50_000

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=get_credential("moonshot"), base_url=_BASE_URL)
    return _client


def submit_batch(requests: list[dict], job_name: str) -> str:
    """构造 JSONL -> 上传 -> 提交 batch -> 返回 batch_id。

    requests 中每个 dict 须含 custom_id 和 body（完整 chat completion 请求参数）。
    单文件最多 50,000 行。
    """
    if len(requests) > _MAX_LINES:
        raise ValueError(f"单文件最多 {_MAX_LINES} 行，实际 {len(requests)} 行")

    input_dir = _BATCH_DIR / "inputs"
    input_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = input_dir / f"{job_name}.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for req in requests:
            line = {
                "custom_id": req["custom_id"],
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": req["body"],
            }
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    client = _get_client()

    with open(jsonl_path, "rb") as f:
        file_obj = client.files.create(file=f, purpose="batch")

    batch = client.batches.create(
        input_file_id=file_obj.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
    )
    return batch.id


def check_batch(batch_id: str) -> dict:
    """查询 batch 状态，返回 {"status": str, "counts": dict}。"""
    client = _get_client()
    batch = client.batches.retrieve(batch_id)
    counts = batch.request_counts
    return {
        "status": batch.status,
        "counts": {
            "total": counts.total,
            "completed": counts.completed,
            "failed": counts.failed,
        },
    }


def retrieve_batch(batch_id: str, job_name: str = "") -> list[dict]:
    """拉取已完成 batch 的结果并持久化。

    返回 list[dict]，每个含 custom_id 和 response。
    """
    client = _get_client()
    batch = client.batches.retrieve(batch_id)

    if not batch.output_file_id:
        raise RuntimeError(
            f"batch {batch_id} 无 output_file_id，当前 status={batch.status}"
        )

    content = client.files.content(batch.output_file_id)
    raw_text = content.text

    results: list[dict] = []
    for line in raw_text.strip().splitlines():
        obj = json.loads(line)
        results.append({
            "custom_id": obj["custom_id"],
            "response": obj["response"],
        })

    if job_name:
        output_dir = _BATCH_DIR / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{job_name}_result.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    return results
