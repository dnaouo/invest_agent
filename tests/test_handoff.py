import pytest
from pathlib import Path
from harness.handoff import HandoffArtifact, save_handoff, load_handoff


def test_save_and_load(tmp_path):
    artifact = HandoffArtifact(
        date="20260502",
        positions=[{"ts_code": "000988.SZ", "pct": 5.0}],
        pending_signals=[{"ts_code": "001267.SZ", "direction": "buy"}],
        learnings=["应收账款需重点关注"],
        focus_themes=["CPO", "光模块"],
        blacklist_today=["000001.SZ"],
    )

    path = save_handoff(artifact, handoff_dir=tmp_path)
    assert path.exists()

    loaded = load_handoff("20260502", handoff_dir=tmp_path)
    assert loaded is not None
    assert loaded.date == "20260502"
    assert len(loaded.positions) == 1
    assert loaded.positions[0]["ts_code"] == "000988.SZ"
    assert loaded.focus_themes == ["CPO", "光模块"]


def test_load_nonexistent(tmp_path):
    result = load_handoff("19990101", handoff_dir=tmp_path)
    assert result is None


def test_handoff_empty_fields():
    artifact = HandoffArtifact(date="20260502")
    assert artifact.positions == []
    assert artifact.learnings == []


def test_save_overwrites(tmp_path):
    a1 = HandoffArtifact(date="20260502", learnings=["v1"])
    save_handoff(a1, handoff_dir=tmp_path)

    a2 = HandoffArtifact(date="20260502", learnings=["v2"])
    save_handoff(a2, handoff_dir=tmp_path)

    loaded = load_handoff("20260502", handoff_dir=tmp_path)
    assert loaded.learnings == ["v2"]
