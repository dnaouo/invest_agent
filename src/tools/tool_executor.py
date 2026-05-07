"""Tool Calling 多轮执行器 — LLM 调 tool -> 执行 -> 结果回传 -> 重复。"""
from __future__ import annotations

import json

from llm_clients.kimi_sync import call_kimi


def run_agent_with_tools(
    system_prompt: str,
    user_message: str,
    tools: list[dict],
    tool_functions: dict[str, callable],
    tier_config: dict,
    max_rounds: int = 3,
) -> dict:
    """运行带 tool calling 的 agent。

    流程：
    1. 调 Kimi（带 tools 参数）
    2. 如果返回 tool_calls，执行对应函数
    3. 把结果作为 tool message 回传 LLM
    4. 重复直到 LLM 返回最终 content（不再调 tool）
    5. 最多 max_rounds 轮

    返回：{"content": str, "reasoning_content": str|None, "tool_calls_made": list}
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    tool_calls_made = []
    content = ""
    reasoning = None

    for _round_num in range(max_rounds):
        response = call_kimi(
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
            **tier_config,
        )

        content = response.get("content", "")
        tool_calls = response.get("tool_calls")
        reasoning = response.get("reasoning_content")

        if not tool_calls:
            return {
                "content": content,
                "reasoning_content": reasoning,
                "tool_calls_made": tool_calls_made,
            }

        assistant_msg = {"role": "assistant", "content": content or ""}
        if reasoning:
            assistant_msg["reasoning_content"] = reasoning
        assistant_msg["tool_calls"] = []
        for tc in tool_calls:
            tc_dict = {
                "id": tc.id if hasattr(tc, "id") else str(tc.get("id", "")),
                "type": "function",
                "function": {
                    "name": tc.function.name if hasattr(tc, "function") else tc.get("function", {}).get("name", ""),
                    "arguments": tc.function.arguments if hasattr(tc, "function") else tc.get("function", {}).get("arguments", "{}"),
                },
            }
            assistant_msg["tool_calls"].append(tc_dict)
        messages.append(assistant_msg)

        for tc in tool_calls:
            func_name = tc.function.name if hasattr(tc, "function") else tc.get("function", {}).get("name", "")
            args_str = tc.function.arguments if hasattr(tc, "function") else tc.get("function", {}).get("arguments", "{}")
            tc_id = tc.id if hasattr(tc, "id") else str(tc.get("id", ""))

            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                args = {}

            func = tool_functions.get(func_name)
            if func:
                try:
                    result = func(**args)
                except Exception as e:
                    result = f"Tool 执行失败: {e}"
            else:
                result = f"未知 tool: {func_name}"

            tool_calls_made.append({"name": func_name, "args": args, "result": str(result)[:500]})

            messages.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": str(result),
            })

    return {
        "content": content or "分析超过最大轮次",
        "reasoning_content": reasoning,
        "tool_calls_made": tool_calls_made,
    }
