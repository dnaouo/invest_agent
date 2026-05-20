"""LanceDB 语义知识库 — 存储公告/研报正文的 embedding，支持语义检索。"""

import os
from pathlib import Path

_DB_PATH = Path("data/lancedb")
_TABLE_NAME = "knowledge"

_model = None


def _get_db():
    """懒加载 LanceDB 连接。"""
    import lancedb
    _DB_PATH.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(_DB_PATH))


def _get_embedding_model():
    """获取 embedding 模型（本地 sentence-transformers）。

    使用 BAAI/bge-small-zh-v1.5（中文优化，384维，模型小巧）。
    首次调用会自动下载模型（约 90MB）。
    """
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("BAAI/bge-small-zh-v1.5")


def _embed(texts: list[str]) -> list[list[float]]:
    """批量 embedding。"""
    global _model
    if _model is None:
        _model = _get_embedding_model()
    embeddings = _model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """将长文本分块。"""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def ingest(ts_code: str, title: str, text: str, source_type: str = "announcement",
           ann_date: str = "") -> int:
    """
    将文本分块并入库 LanceDB。

    Returns:
        入库的 chunk 数量
    """
    if not text or len(text.strip()) < 50:
        return 0

    chunks = _chunk_text(text)
    embeddings = _embed(chunks)

    records = []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        records.append({
            "ts_code": ts_code,
            "title": title,
            "text": chunk,
            "source_type": source_type,
            "ann_date": ann_date,
            "chunk_idx": i,
            "vector": emb,
        })

    db = _get_db()
    if _TABLE_NAME in db.table_names():
        table = db.open_table(_TABLE_NAME)
        table.add(records)
    else:
        db.create_table(_TABLE_NAME, records)

    return len(records)


def semantic_search(query: str, ts_code: str = "", source_type: str = "",
                    top_k: int = 5) -> list[dict]:
    """
    语义检索。

    Returns:
        [{"ts_code", "title", "text", "source_type", "ann_date", "score"}, ...]
    """
    db = _get_db()
    if _TABLE_NAME not in db.table_names():
        return []

    table = db.open_table(_TABLE_NAME)
    query_embedding = _embed([query])[0]

    results = table.search(query_embedding).limit(top_k * 3)

    if ts_code:
        code6 = ts_code.split(".")[0]
        safe_code = code6.replace("'", "").replace(";", "").replace("--", "")[:10]
        results = results.where(f"ts_code LIKE '%{safe_code}%'")
    if source_type:
        allowed_types = {"announcement", "report", "policy"}
        if source_type in allowed_types:
            results = results.where(f"source_type = '{source_type}'")

    results = results.limit(top_k).to_pandas()

    output = []
    for _, row in results.iterrows():
        output.append({
            "ts_code": row.get("ts_code", ""),
            "title": row.get("title", ""),
            "text": row.get("text", ""),
            "source_type": row.get("source_type", ""),
            "ann_date": row.get("ann_date", ""),
            "score": float(row.get("_distance", 0)),
        })

    return output


def ingest_announcement(ts_code: str, title: str, text: str, ann_date: str = "") -> int:
    """便捷函数：入库公告正文。"""
    return ingest(ts_code=ts_code, title=title, text=text,
                  source_type="announcement", ann_date=ann_date)


def ingest_report(ts_code: str, title: str, abstract: str, ann_date: str = "") -> int:
    """便捷函数：入库研报摘要。"""
    return ingest(ts_code=ts_code, title=title, text=abstract,
                  source_type="report", ann_date=ann_date)


def ingest_policy(title: str, content: str, ann_date: str = "") -> int:
    """便捷函数：入库政策正文。"""
    return ingest(ts_code="", title=title, text=content,
                  source_type="policy", ann_date=ann_date)
