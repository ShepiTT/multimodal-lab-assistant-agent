"""Agent 主循环：OpenAI function-calling 风格的"思考→调工具→整合"迭代。

模型客户端通过 client_factory 注入，默认按 models_config.json 解析
（复用 llm_runner 的 provider 配置），测试时可注入 stub。
"""
import json
from typing import Any, Callable, Dict, List, Optional

from ..observability import get_logger
from .tools import execute_tool, get_tool_schemas

logger = get_logger()

MAX_ITERATIONS = 6

AGENT_SYSTEM_PROMPT = """你是实验室多模态智能助手 Agent。你可以调用工具来回答问题：
- 涉及实验操作/故障/安全/代码的专业问题，优先调用 search_knowledge_base 检索私有知识库；
- 需要验证代码时调用 run_code 在沙箱中实际执行；
- 给出任何操作建议前，先用 assess_safety_risk 检查安全风险；风险为 high 时必须先给出安全警示；
- 知识库没有的通用信息可用 search_web。
回答时引用工具返回的来源（source 字段）。不要编造知识库中不存在的内容。"""


def _default_client_factory(provider_id: Optional[str], api_key: Optional[str],
                            base_url: Optional[str]):
    """按 models_config.json 的 provider 配置创建 OpenAI 兼容客户端。"""
    from openai import OpenAI
    from models.LLM.llm_runner import (
        load_config, find_provider, resolve_api_key, resolve_base_url,
    )
    cfg = load_config()
    provider = find_provider(cfg, provider_id)
    key = resolve_api_key(provider, api_key)
    if not key:
        raise RuntimeError("缺少 API Key，无法创建模型客户端")
    url = resolve_base_url(provider, base_url)
    return OpenAI(api_key=key, base_url=url or None), provider


def run_agent(message: str,
              provider_id: Optional[str] = None,
              model_id: Optional[str] = None,
              system_prompt: str = "",
              api_key: Optional[str] = None,
              base_url: Optional[str] = None,
              max_iterations: int = MAX_ITERATIONS,
              client_factory: Callable = None) -> Dict[str, Any]:
    """运行工具调用 Agent，返回 {'answer', 'tool_trace', 'iterations'}。

    tool_trace: [{'tool', 'arguments', 'result'}]，按调用顺序。
    """
    factory = client_factory or _default_client_factory
    client, provider = factory(provider_id, api_key, base_url)

    if model_id is None:
        from models.LLM.llm_runner import find_model
        model_id = find_model(provider, None).get("id")

    messages: List[Dict] = [
        {"role": "system", "content": (system_prompt or "") + "\n" + AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": message},
    ]
    tool_trace: List[Dict] = []

    for iteration in range(1, max_iterations + 1):
        resp = client.chat.completions.create(
            model=model_id,
            messages=messages,
            tools=get_tool_schemas(),
        )
        choice = resp.choices[0]
        msg = choice.message

        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            # 无工具调用 → 最终回答
            return {
                "answer": msg.content or "",
                "tool_trace": tool_trace,
                "iterations": iteration,
            }

        # 记录 assistant 的工具调用消息
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name,
                                 "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ],
        })

        # 逐个执行工具并回填结果
        for tc in tool_calls:
            name = tc.function.name
            args = tc.function.arguments
            logger.info(f"[Agent] 第{iteration}轮 调用工具 {name}")
            result = execute_tool(name, args)
            tool_trace.append({
                "tool": name,
                "arguments": args if isinstance(args, dict) else str(args),
                "result": result,
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False)[:8000],
            })

    # 达到迭代上限：让调用方知道未收敛
    return {
        "answer": "（已达到最大工具调用轮数，基于已获取的信息无法给出完整回答）",
        "tool_trace": tool_trace,
        "iterations": max_iterations,
        "truncated": True,
    }
