"""LLM-as-judge — 用 Kimi 对信号质量打分。"""
from __future__ import annotations
import json
from llm_clients.kimi_sync import call_kimi
from llm_clients.tier_router import get_tier_config

_RUBRIC = """评分维度（每项 0-1 分）：
1. 事实准确：引用的数据是否准确
2. 数据引用：是否引用了具体数据源
3. 逻辑严密：推理过程是否合理
4. 风险识别：是否充分识别了风险
总分 = 4 项平均值"""


def judge_signal(signal: dict, context: str = "") -> dict:
    """对一个投资信号进行质量评分。
    返回 {"overall": 0-1, "fact_accuracy": 0-1, "data_citation": 0-1, "logic": 0-1, "risk_awareness": 0-1}
    """
    tier = get_tier_config("critic")
    prompt = (
        f"你是投资信号质量评审员。\n\n{_RUBRIC}\n\n"
        f"待评审信号：\n{json.dumps(signal, ensure_ascii=False, default=str)}\n\n"
        f"背景信息：{context or '无'}\n\n"
        '输出 JSON：{"fact_accuracy":0-1, "data_citation":0-1, '
        '"logic":0-1, "risk_awareness":0-1, "overall":0-1}'
    )

    response = call_kimi(messages=[{"role": "user", "content": prompt}], **tier)
    content = response["content"]
    try:
        start = content.index("{")
        end = content.rindex("}") + 1
        result = json.loads(content[start:end])
        if "overall" not in result:
            scores = [
                result.get("fact_accuracy", 0),
                result.get("data_citation", 0),
                result.get("logic", 0),
                result.get("risk_awareness", 0),
            ]
            result["overall"] = sum(scores) / len(scores) if scores else 0
        return result
    except (ValueError, json.JSONDecodeError):
        return {
            "overall": 0.5,
            "fact_accuracy": 0.5,
            "data_citation": 0.5,
            "logic": 0.5,
            "risk_awareness": 0.5,
            "_parse_failed": True,
        }
