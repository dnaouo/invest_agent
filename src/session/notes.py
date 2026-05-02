"""每日复盘 notes 读写。"""
from __future__ import annotations
from pathlib import Path

_NOTES_DIR = Path("data/notes")


def write_note(date: str, content: str, notes_dir: Path | None = None) -> Path:
    """写入每日 note 到 data/notes/{date}.md。返回文件路径。"""
    d = notes_dir or _NOTES_DIR
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{date}.md"
    path.write_text(content, encoding="utf-8")
    return path


def read_note(date: str, notes_dir: Path | None = None) -> str | None:
    """读取每日 note。不存在返回 None。"""
    d = notes_dir or _NOTES_DIR
    path = d / f"{date}.md"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")
