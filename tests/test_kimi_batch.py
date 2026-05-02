"""Tests for llm_clients.kimi_batch — all API calls are mocked."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

import llm_clients.kimi_batch as _mod
from llm_clients.kimi_batch import check_batch, retrieve_batch, submit_batch


@pytest.fixture(autouse=True)
def _reset_client():
    _mod._client = None
    yield
    _mod._client = None


def _sample_requests() -> list[dict]:
    return [
        {
            "custom_id": "req_001",
            "body": {
                "model": "kimi-k2.6",
                "messages": [{"role": "user", "content": "hello"}],
                "max_tokens": 4096,
            },
        },
        {
            "custom_id": "req_002",
            "body": {
                "model": "kimi-k2.6",
                "messages": [{"role": "user", "content": "world"}],
                "max_tokens": 4096,
            },
        },
    ]


@patch("llm_clients.kimi_batch.OpenAI")
def test_submit_batch(mock_openai_cls: MagicMock, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(_mod, "_BATCH_DIR", tmp_path / "batch_jobs")

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    mock_file = MagicMock()
    mock_file.id = "file-abc123"
    mock_client.files.create.return_value = mock_file

    mock_batch = MagicMock()
    mock_batch.id = "batch-xyz789"
    mock_client.batches.create.return_value = mock_batch

    batch_id = submit_batch(_sample_requests(), "test_job")

    assert batch_id == "batch-xyz789"

    jsonl_path = tmp_path / "batch_jobs" / "inputs" / "test_job.jsonl"
    assert jsonl_path.exists()

    lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["custom_id"] == "req_001"
    assert first["method"] == "POST"
    assert first["url"] == "/v1/chat/completions"
    assert first["body"]["model"] == "kimi-k2.6"

    mock_client.files.create.assert_called_once()
    mock_client.batches.create.assert_called_once_with(
        input_file_id="file-abc123",
        endpoint="/v1/chat/completions",
        completion_window="24h",
    )


@patch("llm_clients.kimi_batch.OpenAI")
def test_submit_batch_exceeds_max_lines(mock_openai_cls: MagicMock, monkeypatch) -> None:
    monkeypatch.setattr(_mod, "_MAX_LINES", 1)
    with pytest.raises(ValueError, match="单文件最多 1 行"):
        submit_batch(_sample_requests(), "too_big")


@patch("llm_clients.kimi_batch.OpenAI")
def test_check_batch(mock_openai_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    mock_batch = MagicMock()
    mock_batch.status = "completed"
    mock_batch.request_counts.total = 10
    mock_batch.request_counts.completed = 10
    mock_batch.request_counts.failed = 0
    mock_client.batches.retrieve.return_value = mock_batch

    result = check_batch("batch-xyz789")

    assert result["status"] == "completed"
    assert result["counts"]["total"] == 10
    assert result["counts"]["completed"] == 10
    assert result["counts"]["failed"] == 0
    mock_client.batches.retrieve.assert_called_once_with("batch-xyz789")


@patch("llm_clients.kimi_batch.OpenAI")
def test_retrieve_batch(mock_openai_cls: MagicMock, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(_mod, "_BATCH_DIR", tmp_path / "batch_jobs")

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    output_lines = [
        json.dumps({"custom_id": "req_001", "response": {"body": {"choices": [{"message": {"content": "hi"}}]}}}),
        json.dumps({"custom_id": "req_002", "response": {"body": {"choices": [{"message": {"content": "yo"}}]}}}),
    ]

    mock_batch = MagicMock()
    mock_batch.status = "completed"
    mock_batch.output_file_id = "file-out456"
    mock_client.batches.retrieve.return_value = mock_batch

    mock_content = MagicMock()
    mock_content.text = "\n".join(output_lines)
    mock_client.files.content.return_value = mock_content

    results = retrieve_batch("batch-xyz789", job_name="test_job")

    assert len(results) == 2
    assert results[0]["custom_id"] == "req_001"
    assert results[1]["custom_id"] == "req_002"
    assert "response" in results[0]

    out_path = tmp_path / "batch_jobs" / "outputs" / "test_job_result.jsonl"
    assert out_path.exists()

    mock_client.files.content.assert_called_once_with("file-out456")


@patch("llm_clients.kimi_batch.OpenAI")
def test_retrieve_batch_no_output_file(mock_openai_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    mock_batch = MagicMock()
    mock_batch.status = "in_progress"
    mock_batch.output_file_id = None
    mock_client.batches.retrieve.return_value = mock_batch

    with pytest.raises(RuntimeError, match="无 output_file_id"):
        retrieve_batch("batch-xyz789")
