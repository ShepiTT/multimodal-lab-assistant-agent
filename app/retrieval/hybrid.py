"""混合检索管线：Dense + BM25 → RRF 融合 →（可选）精排 → 父块上下文扩展。

包装既有的知识库实例（FaultDiagnosisKnowledgeBase），不修改其索引格式：
- Dense 召回复用 kb 的向量检索
- BM25 索引在内存中基于 kb.vector_store.documents 构建并按知识库缓存
- 父块上下文：优先使用切分时保存的 parent_content 元数据（parent_child
  切分法），否则用同文档相邻块拼接近似
"""
from typing import Any, Dict, List

from .bm25 import BM25Index
from .fusion import rrf_fuse
from . import reranker

# 初始召回规模与融合后保留规模（方案推荐值）
DENSE_CANDIDATES = 20
BM25_CANDIDATES = 20
FUSED_KEEP = 10


class HybridSearcher:
    def __init__(self, kb):
        """kb: 已加载索引的 FaultDiagnosisKnowledgeBase 实例。"""
        self.kb = kb
        self._bm25 = None
        self._bm25_doc_count = -1

    def _get_bm25(self) -> BM25Index:
        docs = self.kb.vector_store.documents
        # 索引重建后文档数变化，BM25 随之重建
        if self._bm25 is None or self._bm25_doc_count != len(docs):
            self._bm25 = BM25Index(docs)
            self._bm25_doc_count = len(docs)
        return self._bm25

    def _expand_context(self, idx: int) -> str:
        """取命中块的父级上下文：优先 parent_content，否则相邻块拼接。"""
        store = self.kb.vector_store
        meta = store.metadata[idx]

        parent = meta.get('parent_content')
        if parent:
            return parent

        # 相邻块近似：同一文档内 chunk_id ±1 的块按序拼接
        source = meta.get('source')
        chunk_id = meta.get('chunk_id')
        if source is None or chunk_id is None:
            return store.documents[idx]

        pieces = {}
        for j, m in enumerate(store.metadata):
            if m.get('source') == source and m.get('chunk_id') in (chunk_id - 1, chunk_id, chunk_id + 1):
                pieces[m.get('chunk_id')] = store.documents[j]
        return "\n".join(pieces[k] for k in sorted(pieces))

    def search(self, query: str, top_k: int = 5, use_rerank: bool = True) -> List[Dict[str, Any]]:
        """混合检索，返回与 kb.search 兼容的结果结构（多出 context/retrieval 字段）。"""
        store = self.kb.vector_store
        if store is None or store.index.ntotal == 0:
            return []

        # 1. Dense 召回（纯向量，不做关键词加分——字面匹配交给 BM25 这一路）
        query_embedding = self.kb.embedder.encode([query])[0]
        dense_hits = store.search(query_embedding, top_k=min(DENSE_CANDIDATES, store.index.ntotal))
        dense_ranking = [h['index'] for h in dense_hits]
        dense_scores = {h['index']: h['score'] for h in dense_hits}

        # 2. BM25 召回
        bm25_hits = self._get_bm25().search(query, top_k=BM25_CANDIDATES)
        bm25_ranking = [i for i, _ in bm25_hits]
        bm25_scores = dict(bm25_hits)

        # 3. RRF 融合
        fused = rrf_fuse([dense_ranking, bm25_ranking])[:FUSED_KEEP]
        fused_ids = [doc_id for doc_id, _ in fused]
        rrf_scores = dict(fused)

        # 4. 可选精排
        rerank_used = False
        if use_rerank and fused_ids:
            order = reranker.rerank(query, [store.documents[i] for i in fused_ids], top_k=top_k)
            if order is not None:
                fused_ids = [fused_ids[i] for i in order]
                rerank_used = True

        final_ids = fused_ids[:top_k]

        # 5. 组装结果 + 父块上下文扩展（上下文重复的合并去重）
        results = []
        seen_contexts = set()
        for idx in final_ids:
            context = self._expand_context(idx)
            context_key = hash(context)
            duplicated = context_key in seen_contexts
            seen_contexts.add(context_key)

            results.append({
                'document': store.documents[idx],
                'metadata': store.metadata[idx],
                # 主得分沿用 RRF（精排只调序），保证跨路可比且稳定在 (0,1) 区间之外也单调
                'score': round(rrf_scores.get(idx, 0.0), 6),
                'index': int(idx),
                'context': None if duplicated else context,
                'retrieval': {
                    'dense_score': round(dense_scores.get(idx, 0.0), 4) if idx in dense_scores else None,
                    'bm25_score': round(bm25_scores.get(idx, 0.0), 4) if idx in bm25_scores else None,
                    'rrf_score': round(rrf_scores.get(idx, 0.0), 6),
                    'reranked': rerank_used,
                },
            })
        return results


# 按知识库类型缓存 HybridSearcher（kb 实例被清缓存重建后自动跟随）
_searchers: Dict[str, HybridSearcher] = {}


def get_hybrid_searcher(kb_type: str, kb) -> HybridSearcher:
    searcher = _searchers.get(kb_type)
    if searcher is None or searcher.kb is not kb:
        searcher = HybridSearcher(kb)
        _searchers[kb_type] = searcher
    return searcher
