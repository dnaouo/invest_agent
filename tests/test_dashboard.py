"""Tests for observability.dashboard."""
import pytest
from sandboxes.data import duckdb_store
from session.events import emit_event, _INITIALIZED
from observability.dashboard import generate_daily_report


@pytest.fixture(autouse=True)
def _clean_duckdb():
    """每个测试独立内存数据库。"""
    duckdb_store._connections.pop(":memory:", None)
    _INITIALIZED.pop(":memory:", None)
    yield
    duckdb_store._connections.pop(":memory:", None)
    _INITIALIZED.pop(":memory:", None)


def test_generate_daily_report_empty():
    """无 events 表时返回空报告。"""
    report = generate_daily_report("2026-05-03", db_path=":memory:")
    assert report["date"] == "2026-05-03"
    assert report["agents"] == {}
    assert report["total_calls"] == 0
    assert report["total_cost"] == 0.0


def test_generate_daily_report_with_data():
    """先 emit 几条 event，再生成报告，验证统计正确。"""
    sid = "session_2026-05-03_001"
    emit_event(sid, "llm_call", {
        "agent_name": "fund",
        "tokens": 1000,
        "cost": 0.01,
        "latency_ms": 200.0,
    }, db_path=":memory:")
    emit_event(sid, "llm_call", {
        "agent_name": "fund",
        "tokens": 1500,
        "cost": 0.015,
        "latency_ms": 300.0,
    }, db_path=":memory:")
    emit_event(sid, "llm_call", {
        "agent_name": "critic",
        "tokens": 800,
        "cost": 0.008,
        "latency_ms": 150.0,
    }, db_path=":memory:")

    report = generate_daily_report("2026-05-03", db_path=":memory:")

    assert report["date"] == "2026-05-03"
    assert report["total_calls"] == 3
    assert report["total_cost"] == pytest.approx(0.033, abs=1e-4)

    fund = report["agents"]["fund"]
    assert fund["calls"] == 2
    assert fund["cost"] == pytest.approx(0.025, abs=1e-4)
    assert fund["tokens"] == 2500
    assert fund["avg_latency_ms"] == pytest.approx(250.0, abs=0.1)

    critic = report["agents"]["critic"]
    assert critic["calls"] == 1
    assert critic["cost"] == pytest.approx(0.008, abs=1e-4)
