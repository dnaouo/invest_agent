"""Langfuse 可观测性客户端 — 如果未配置则静默降级。"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

_langfuse = None
_disabled = False


def _get_langfuse():
    """懒加载 Langfuse 客户端。未配置时返回 None 且不再重试。"""
    global _langfuse, _disabled
    if _disabled:
        return None
    if _langfuse is not None:
        return _langfuse
    try:
        from langfuse import Langfuse
        from vault.proxy import get_credential

        public_key = get_credential("langfuse_public")
        secret_key = get_credential("langfuse_secret")
        host = get_credential("langfuse_host")
        _langfuse = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
        return _langfuse
    except (ImportError, ValueError, RuntimeError) as e:
        logger.info("Langfuse 未配置，已降级: %s", e)
        _disabled = True
        return None


def trace_llm_call(
    agent_name: str,
    input_text: str,
    output_text: str,
    tokens: int = 0,
    cost: float = 0.0,
    latency_ms: float = 0.0,
    model: str = "kimi-k2.6",
) -> str | None:
    """记录一次 LLM 调用到 Langfuse。未配置时静默返回 None。"""
    lf = _get_langfuse()
    if lf is None:
        return None
    trace = lf.trace(name=f"{agent_name}_llm_call")
    trace.generation(
        name=agent_name,
        model=model,
        input=input_text,
        output=output_text,
        usage={"total_tokens": tokens},
        metadata={"cost": cost, "latency_ms": latency_ms},
    )
    return trace.id


def get_trace_url(trace_id: str) -> str | None:
    """返回 Langfuse UI 链接。未配置时返回 None。"""
    lf = _get_langfuse()
    if lf is None:
        return None
    try:
        host = lf.base_url or "http://localhost:3000"
    except AttributeError:
        host = "http://localhost:3000"
    return f"{host}/trace/{trace_id}"


def flush() -> None:
    """刷新 Langfuse 缓冲区。"""
    lf = _get_langfuse()
    if lf is not None:
        lf.flush()
