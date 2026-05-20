import json
from pathlib import Path
from unittest.mock import patch
import importlib.util

import pytest


def _load_module():
    """动态加载 scripts/compile_deep_report.py，避免 import 路径问题。"""
    path = Path(__file__).resolve().parents[2] / "scripts" / "compile_deep_report.py"
    spec = importlib.util.spec_from_file_location("compile_deep_report", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_atomic_write_does_not_truncate_on_exception(tmp_path):
    """异常情况下不应该 truncate 已存在的报告文件。"""
    report = tmp_path / "report.md"
    report.write_text("旧内容", encoding="utf-8")
    mod = _load_module()
    with patch.object(mod, "load", side_effect=RuntimeError("boom")):
        with patch.object(mod, "REPORT_FILE", report):
            with patch.object(mod, "OUT_DIR", tmp_path / "noexist"):
                try:
                    mod.main()
                except RuntimeError:
                    pass
    assert report.read_text(encoding="utf-8") == "旧内容", "异常时旧文件不应被清空"


def test_main_reads_candidates_from_scan_json(tmp_path, monkeypatch):
    """新版应该从 data/market_scan_*.json 读取候选股，而非 hardcode。"""
    scan_json = tmp_path / "market_scan_20260515.json"
    scan_json.write_text(
        json.dumps({"candidates": [
            {"ts_code": "300054.SZ", "stock_name": "鼎龙股份", "trigger_reason": "测试", "industry": "电子"}
        ]}, ensure_ascii=False),
        encoding="utf-8",
    )
    out_dir = tmp_path / "week_test"
    out_dir.mkdir()
    (out_dir / "300054_SZ.json").write_text(json.dumps({
        "phase1": {"hypothesis": "h", "stock_type": "t"},
        "phase3": {"hypothesis_valid": True, "position_type": "watch", "confidence": 0.5},
        "critic": {"recommendation": "watch", "adjusted_confidence": 0.5},
    }, ensure_ascii=False), encoding="utf-8")
    report = tmp_path / "report.md"
    mod = _load_module()
    monkeypatch.setattr(mod, "OUT_DIR", out_dir)
    monkeypatch.setattr(mod, "REPORT_FILE", report)
    monkeypatch.setattr(mod, "SCAN_JSON", scan_json)
    mod.main()
    assert report.stat().st_size > 50, "报告文件不应为 0 字节"
    content = report.read_text(encoding="utf-8")
    assert "鼎龙股份" in content


def test_dry_run_does_not_write_file(tmp_path, monkeypatch, capsys):
    """--dry-run 应只 print 内容，不创建任何文件。"""
    scan_json = tmp_path / "market_scan_20260515.json"
    scan_json.write_text(
        json.dumps({"candidates": [
            {"ts_code": "300054.SZ", "stock_name": "鼎龙股份", "trigger_reason": "测试", "industry": "电子"}
        ]}, ensure_ascii=False),
        encoding="utf-8",
    )
    out_dir = tmp_path / "week_test"
    out_dir.mkdir()
    (out_dir / "300054_SZ.json").write_text(json.dumps({
        "phase1": {"hypothesis": "h"},
        "phase3": {"position_type": "watch"},
        "critic": {"recommendation": "watch"},
    }, ensure_ascii=False), encoding="utf-8")
    report = tmp_path / "report.md"
    mod = _load_module()
    monkeypatch.setattr(mod, "OUT_DIR", out_dir)
    monkeypatch.setattr(mod, "REPORT_FILE", report)
    monkeypatch.setattr(mod, "SCAN_JSON", scan_json)
    monkeypatch.setattr("sys.argv", ["compile_deep_report.py", "--dry-run"])
    mod.cli()
    assert not report.exists(), "dry-run 不应该写文件"
    captured = capsys.readouterr()
    assert "鼎龙股份" in captured.out


def test_missing_scan_json_raises(tmp_path, monkeypatch):
    """SCAN_JSON 不存在时必须 fail loud（FileNotFoundError）。"""
    mod = _load_module()
    monkeypatch.setattr(mod, "SCAN_JSON", tmp_path / "missing.json")
    with pytest.raises(FileNotFoundError):
        mod.main()
