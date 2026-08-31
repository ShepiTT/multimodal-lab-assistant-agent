"""Agent 工具注册表：把系统既有能力封装为大模型可调用的工具。

每个工具 = OpenAI function-calling 格式的 schema + 一个执行函数。
执行函数只返回可 JSON 序列化的结果；异常被捕获并作为 error 字段返回，
保证 Agent 循环不会因单个工具失败而中断。
"""
import json
from typing import Any, Callable, Dict, List

from .. import runtime
from ..config import KB_TYPE_MAP
from ..observability import get_logger

logger = get_logger()

_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register(name: str, description: str, parameters: Dict) -> Callable:
    """装饰器：注册一个工具。"""
    def deco(func):
        _REGISTRY[name] = {
            "schema": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters,
                },
            },
            "func": func,
        }
        return func
    return deco


# ---- 工具实现 ----

@register(
    "search_knowledge_base",
    "在实验室私有知识库中做混合检索（向量+BM25），返回最相关的知识片段及来源。"
    "kb_type 可选: guide(操作指导) / diagnosis(故障诊断) / safety(安全规范) / debug(代码调试)。",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "检索查询语句"},
            "kb_type": {"type": "string", "enum": list(KB_TYPE_MAP.keys()),
                        "description": "目标知识库类型"},
            "top_k": {"type": "integer", "description": "返回条数，默认 3"},
        },
        "required": ["query", "kb_type"],
    },
)
def search_knowledge_base(query: str, kb_type: str, top_k: int = 3):
    from ..services.kb import get_kb_instance
    from ..retrieval import get_hybrid_searcher

    kb = get_kb_instance(kb_type)
    if kb is None:
        return {"error": f"知识库 {kb_type} 未构建或不可用"}
    searcher = get_hybrid_searcher(kb_type, kb)
    results = searcher.search(query, top_k=top_k, use_rerank=True)
    return {
        "results": [
            {
                "content": r["document"],
                "context": r.get("context"),
                "source": r["metadata"].get("source"),
                "title": r["metadata"].get("title", ""),
                "score": r["score"],
            }
            for r in results
        ]
    }


@register(
    "run_code",
    "在安全沙箱（Docker/Piston）中执行代码并返回 stdout/stderr/退出码。"
    "适用于验证代码是否可运行、复现报错。",
    {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "要执行的完整代码"},
            "language": {"type": "string", "description": "编程语言，如 python、cpp、java、javascript"},
        },
        "required": ["code", "language"],
    },
)
def run_code(code: str, language: str = "python"):
    from models.IDE import CodeExecutor
    executor = CodeExecutor()
    result = executor.execute(code, language)
    return result.to_dict()


@register(
    "search_web",
    "联网搜索外部信息，用于知识库未覆盖的问题（如最新软件版本、通用报错）。",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "max_results": {"type": "integer", "description": "结果条数，默认 5"},
        },
        "required": ["query"],
    },
)
def search_web(query: str, max_results: int = 5):
    if not runtime.WEB_SEARCH_AVAILABLE:
        return {"error": "联网搜索未启用"}
    return runtime.search_and_format(query, max_results=max_results)


@register(
    "assess_safety_risk",
    "对一段操作描述做实验室安全风险评估（硬规则），返回风险等级与涉及类别。"
    "在给出任何操作建议前，应先用它检查是否涉及高风险操作。",
    {
        "type": "object",
        "properties": {
            "operation": {"type": "string", "description": "拟进行的操作描述"},
        },
        "required": ["operation"],
    },
)
def assess_safety_risk(operation: str):
    from ..security.safety_rules import assess_risk
    return assess_risk(operation)


# ---- 对外接口 ----

def list_tools() -> List[str]:
    return list(_REGISTRY.keys())


TOOL_SCHEMAS = [entry["schema"] for entry in _REGISTRY.values()]


def get_tool_schemas() -> List[Dict]:
    return [entry["schema"] for entry in _REGISTRY.values()]


def execute_tool(name: str, arguments) -> Dict[str, Any]:
    """执行工具；参数可为 dict 或 JSON 字符串。异常转为 error 字段。"""
    entry = _REGISTRY.get(name)
    if entry is None:
        return {"error": f"未知工具: {name}"}

    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments) if arguments.strip() else {}
        except json.JSONDecodeError as e:
            return {"error": f"工具参数不是合法 JSON: {e}"}

    try:
        result = entry["func"](**(arguments or {}))
        return result if isinstance(result, dict) else {"result": result}
    except TypeError as e:
        return {"error": f"工具参数错误: {e}"}
    except Exception as e:
        logger.error(f"[Agent] 工具 {name} 执行失败: {e}")
        return {"error": f"工具执行失败: {e}"}
