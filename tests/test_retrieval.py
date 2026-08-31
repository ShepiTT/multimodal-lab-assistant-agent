"""RAG 检索组件单元测试：BM25、RRF 融合、父子分块、混合检索管线。"""
import numpy as np
import pytest

from app.retrieval.bm25 import BM25Index, tokenize
from app.retrieval.fusion import rrf_fuse
from app.retrieval.hybrid import HybridSearcher


# ---- BM25 ----

DOCS = [
    "示波器探头校准步骤：连接探头到校准输出端，调节补偿电容。",
    "电源模块 PWR-3060 故障代码 E404 表示输出过压保护触发。",
    "实验室安全规范：高压实验必须两人在场，断电后方可接线。",
    "Python 报错 ModuleNotFoundError 通常是依赖未安装导致的。",
]


def test_tokenize_keeps_model_numbers_and_error_codes():
    tokens = tokenize("PWR-3060 报错 E404 怎么处理")
    assert "pwr-3060" in tokens
    assert "e404" in tokens


def test_bm25_exact_term_match_ranks_first():
    idx = BM25Index(DOCS)
    hits = idx.search("E404 故障代码")
    assert hits, "应有命中"
    assert hits[0][0] == 1, "包含 E404 的文档应排第一"


def test_bm25_chinese_semantic_terms():
    idx = BM25Index(DOCS)
    hits = idx.search("探头校准")
    assert hits and hits[0][0] == 0


def test_bm25_empty_and_no_match():
    idx = BM25Index(DOCS)
    assert idx.search("") == []
    assert idx.search("量子纠缠退相干") == []
    assert BM25Index([]).search("任何查询") == []


# ---- RRF ----

def test_rrf_rewards_docs_in_both_rankings():
    # doc 5 在两路都排第二；doc 1 和 doc 9 各只出现一路第一
    fused = rrf_fuse([[1, 5, 2], [9, 5, 3]])
    assert fused[0][0] == 5


def test_rrf_single_ranking_preserves_order():
    fused = rrf_fuse([[3, 1, 2]])
    assert [d for d, _ in fused] == [3, 1, 2]


def test_rrf_weights():
    # 权重压倒排名：第二路权重极高时其第一名胜出
    fused = rrf_fuse([[1, 2], [2, 1]], weights=[1.0, 10.0])
    assert fused[0][0] == 2


# ---- 父子分块 ----

def test_parent_child_chunker():
    import sys
    from pathlib import Path
    kb_root = Path(__file__).resolve().parent.parent / "knowledge_base"
    if str(kb_root) not in sys.path:
        sys.path.insert(0, str(kb_root))
    from chunking.Parent_Child_Chunking import ParentChildChunker

    text = "\n\n".join(
        f"# 第{i}章 标题{i}\n\n" + f"这是第{i}章的内容句子。" * 40
        for i in range(1, 4)
    )
    chunker = ParentChildChunker(parent_size=1200, child_size=300)
    chunks = chunker.chunk(text)

    assert chunks, "应产出子块"
    for c in chunks:
        assert 'parent_id' in c and 'parent_content' in c
        assert c['content'] in c['parent_content'].replace('\n\n', '\n') or c['content'] in c['parent_content'] or len(c['content']) <= 400
        assert len(c['content']) <= 400 + 50, f"子块过长: {len(c['content'])}"
    # 父块应大于子块粒度
    parents = {c['parent_id']: c['parent_content'] for c in chunks}
    assert any(len(p) > 400 for p in parents.values())


def test_parent_child_protects_code_blocks():
    import sys
    from pathlib import Path
    kb_root = Path(__file__).resolve().parent.parent / "knowledge_base"
    if str(kb_root) not in sys.path:
        sys.path.insert(0, str(kb_root))
    from chunking.Parent_Child_Chunking import ParentChildChunker

    code = "```python\n" + "print('hello')\n" * 30 + "```"
    text = f"说明文字。\n\n{code}\n\n结尾文字。"
    chunks = ParentChildChunker().chunk(text)
    code_chunks = [c for c in chunks if c['content'].startswith('```')]
    assert code_chunks, "代码块应作为整体子块保留"
    assert code_chunks[0]['content'].endswith('```'), "代码块不应被截断"


# ---- 混合检索管线（stub 知识库，不依赖真实模型）----

class _StubIndex:
    def __init__(self, n):
        self.ntotal = n


class _StubStore:
    """模拟 FAISSVectorStore：dense 检索按预设顺序返回。"""

    def __init__(self, documents, metadata, dense_order):
        self.documents = documents
        self.metadata = metadata
        self.index = _StubIndex(len(documents))
        self._dense_order = dense_order

    def search(self, query_embedding, top_k):
        return [
            {'document': self.documents[i], 'metadata': self.metadata[i],
             'score': 1.0 - rank * 0.1, 'index': i}
            for rank, i in enumerate(self._dense_order[:top_k])
        ]


class _StubEmbedder:
    def encode(self, texts):
        return np.zeros((len(texts), 8), dtype='float32')


class _StubKB:
    def __init__(self, documents, metadata, dense_order):
        self.vector_store = _StubStore(documents, metadata, dense_order)
        self.embedder = _StubEmbedder()


def _make_kb():
    docs = DOCS
    metadata = [
        {'source': 'scope.md', 'chunk_id': 0, 'title': '探头校准'},
        {'source': 'power.md', 'chunk_id': 0, 'title': '故障代码'},
        {'source': 'safety.md', 'chunk_id': 0, 'title': '安全规范'},
        {'source': 'debug.md', 'chunk_id': 0, 'title': '报错处理'},
    ]
    # dense 召回故意把 E404 文档排最后，验证 BM25 + RRF 能把它拉回前列
    return _StubKB(docs, metadata, dense_order=[0, 2, 3, 1])


def test_hybrid_fuses_bm25_and_dense(monkeypatch):
    monkeypatch.delenv("RERANKER_ENABLED", raising=False)
    searcher = HybridSearcher(_make_kb())
    results = searcher.search("电源 E404 故障代码", top_k=3, use_rerank=False)

    assert results
    top_indices = [r['index'] for r in results]
    assert 1 in top_indices[:2], f"BM25 精确命中的 E404 文档应进前二，实际: {top_indices}"
    for r in results:
        assert 'context' in r
        assert 'retrieval' in r and 'rrf_score' in r['retrieval']


def test_hybrid_context_uses_parent_content():
    docs = ["子块A", "子块B"]
    metadata = [
        {'source': 'a.md', 'chunk_id': 0, 'parent_id': 0, 'parent_content': '父块完整内容 AAAA'},
        {'source': 'a.md', 'chunk_id': 1, 'parent_id': 0, 'parent_content': '父块完整内容 AAAA'},
    ]
    searcher = HybridSearcher(_StubKB(docs, metadata, dense_order=[0, 1]))
    results = searcher.search("子块", top_k=2, use_rerank=False)
    contexts = [r['context'] for r in results]
    assert contexts[0] == '父块完整内容 AAAA'
    # 相同父块只输出一次，重复的置 None 去重
    assert contexts.count('父块完整内容 AAAA') == 1


def test_hybrid_neighbor_expansion_without_parent():
    docs = ["块0内容", "块1内容", "块2内容"]
    metadata = [{'source': 'x.md', 'chunk_id': i} for i in range(3)]
    searcher = HybridSearcher(_StubKB(docs, metadata, dense_order=[1, 0, 2]))
    results = searcher.search("块1", top_k=1, use_rerank=False)
    # 命中块1 → 上下文应拼接相邻的块0、块1、块2
    assert results[0]['context'] == "块0内容\n块1内容\n块2内容"


# ---- API 层 ----

def test_kb_search_rejects_invalid_mode(client):
    r = client.post('/api/kb/search', json={'query': 'x', 'mode': 'nonsense'})
    assert r.status_code in (400, 500)
    if r.status_code == 400:
        assert '模式' in r.get_json().get('error', '')


def test_capabilities_reports_reranker(client):
    caps = client.get('/health/capabilities').get_json()
    assert 'reranker' in caps
