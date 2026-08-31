"""Cross-Encoder 精排（可选组件）。

默认关闭（RERANKER_ENABLED=false），避免强制下载模型；开启后首次调用
懒加载 CrossEncoder（默认 BAAI/bge-reranker-base，可用 RERANKER_MODEL
覆盖，如 Qwen/Qwen3-Reranker-0.6B）。加载失败自动降级为不精排。
"""
import os
from typing import List, Optional

_reranker = None
_load_failed = False


def reranker_enabled() -> bool:
    return os.environ.get("RERANKER_ENABLED", "false").lower() in ("true", "1", "yes")


def _get_model():
    global _reranker, _load_failed
    if _reranker is not None or _load_failed:
        return _reranker
    try:
        from sentence_transformers import CrossEncoder
        model_name = os.environ.get("RERANKER_MODEL", "BAAI/bge-reranker-base")
        print(f"[Reranker] 正在加载精排模型: {model_name}")
        _reranker = CrossEncoder(model_name, max_length=512)
        print("[Reranker] 精排模型加载成功")
    except Exception as e:
        print(f"[Reranker] 精排模型加载失败，降级为不精排: {e}")
        _load_failed = True
    return _reranker


def is_available() -> bool:
    """报告精排能力状态（不触发模型下载/加载）。"""
    return reranker_enabled() and not _load_failed


def rerank(query: str, documents: List[str], top_k: int = 5) -> Optional[List[int]]:
    """对候选文档精排，返回按相关度降序的文档下标列表。

    未启用或模型不可用时返回 None（调用方保持原序）。
    """
    if not reranker_enabled():
        return None
    model = _get_model()
    if model is None:
        return None

    pairs = [(query, doc) for doc in documents]
    scores = model.predict(pairs)
    order = sorted(range(len(documents)), key=lambda i: float(scores[i]), reverse=True)
    return order[:top_k]
