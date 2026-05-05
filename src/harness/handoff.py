"""跨日 handoff artifact — 每日收盘后保存，次日开盘前加载。"""
from __future__ import annotations
import json
from pathlib import Path
from pydantic import BaseModel, Field


_HANDOFF_DIR = Path("data/handoffs")


class HandoffArtifact(BaseModel):
    """每日交付物。"""
    date: str
    positions: list[dict] = Field(default_factory=list, description="当前持仓")
    pending_signals: list[dict] = Field(default_factory=list, description="待确认信号")
    learnings: list[str] = Field(default_factory=list, description="今日教训")
    focus_themes: list[str] = Field(default_factory=list, description="明日关注主线")
    blacklist_today: list[str] = Field(default_factory=list, description="今日黑名单标的")


def save_handoff(artifact: HandoffArtifact, handoff_dir: Path | None = None) -> Path:
    """保存 handoff artifact 到 data/handoffs/{date}.json。返回文件路径。"""
    d = handoff_dir or _HANDOFF_DIR
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{artifact.date}.json"
    path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_handoff(date: str, handoff_dir: Path | None = None) -> HandoffArtifact | None:
    """加载指定日期的 handoff artifact。不存在返回 None。"""
    d = handoff_dir or _HANDOFF_DIR
    path = d / f"{date}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return HandoffArtifact(**data)
