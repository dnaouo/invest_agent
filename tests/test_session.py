import pytest
from session.events import emit_event, get_events, wake, _INITIALIZED
from session.notes import write_note, read_note
from sandboxes.data import duckdb_store


class TestEvents:
    @pytest.fixture(autouse=True)
    def _reset(self):
        _INITIALIZED.clear()
        duckdb_store._connections.pop(":memory:", None)
        yield
        _INITIALIZED.clear()
        duckdb_store._connections.pop(":memory:", None)

    def test_emit_and_get(self):
        db = ":memory:"
        eid = emit_event("sess1", "llm_call", {
            "agent_name": "fund",
            "output": "test output",
            "tokens": 100,
            "model": "kimi-k2.6",
        }, db_path=db)
        assert eid  # non-empty uuid
        events = get_events("sess1", db_path=db)
        assert len(events) == 1
        assert events[0]["agent_name"] == "fund"
        assert events[0]["tokens"] == 100

    def test_get_events_filter(self):
        db = ":memory:"
        emit_event("sess1", "llm_call", {"agent_name": "fund"}, db_path=db)
        emit_event("sess1", "tool_call", {"agent_name": "fund"}, db_path=db)
        llm_events = get_events("sess1", event_type="llm_call", db_path=db)
        assert len(llm_events) == 1

    def test_get_events_empty_session(self):
        db = ":memory:"
        emit_event("sess_other", "llm_call", {}, db_path=db)
        events = get_events("sess_nonexistent", db_path=db)
        assert events == []

    def test_wake_new_session(self):
        db = ":memory:"
        result = wake("brand_new_session", db_path=db)
        assert result["is_new"] is True
        assert result["session_id"] == "brand_new_session"
        assert result["event_count"] == 0
        events = get_events("brand_new_session", db_path=db)
        assert len(events) == 1
        assert events[0]["event_type"] == "session_start"
        assert events[0]["agent_name"] == "system"

    def test_wake_existing_session(self):
        db = ":memory:"
        emit_event("existing_sess", "llm_call", {"agent_name": "fund"}, db_path=db)
        emit_event("existing_sess", "tool_call", {"agent_name": "macro"}, db_path=db)
        emit_event("existing_sess", "llm_call", {"agent_name": "sector"}, db_path=db)
        result = wake("existing_sess", db_path=db)
        assert result["is_new"] is False
        assert result["session_id"] == "existing_sess"
        assert result["event_count"] == 3
        assert result["last_event_type"] == "llm_call"
        assert result["last_agent"] == "sector"


class TestNotes:
    def test_write_and_read(self, tmp_path):
        write_note("2026-05-02", "# 今日复盘\n测试内容", notes_dir=tmp_path)
        content = read_note("2026-05-02", notes_dir=tmp_path)
        assert "今日复盘" in content

    def test_read_nonexistent(self, tmp_path):
        assert read_note("1999-01-01", notes_dir=tmp_path) is None
