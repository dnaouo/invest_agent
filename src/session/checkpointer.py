"""LangGraph SQLite checkpointer 封装。"""
from __future__ import annotations
from pathlib import Path

_DEFAULT_CHECKPOINT_DB = "data/checkpoints/langgraph.sqlite"


def get_checkpointer(db_path: str | None = None):
    """返回 LangGraph SqliteSaver 实例。
    如果 langgraph 未安装，抛出 ImportError 并给出明确提示。"""
    db_path = db_path or _DEFAULT_CHECKPOINT_DB
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError:
        raise ImportError(
            "langgraph 未安装。请运行: pip install langgraph"
        )
    return SqliteSaver.from_conn_string(db_path)
