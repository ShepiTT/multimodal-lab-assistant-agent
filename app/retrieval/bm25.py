"""BM25 稀疏检索（Okapi BM25，jieba 中文分词）。

纯 Python 实现，无额外依赖；用于补足 Dense 向量检索在精确型号、
错误码、专有名词等字面匹配场景下的召回短板。
"""
import math
import re
from collections import Counter
from typing import Dict, List, Tuple

_STOPWORDS = {
    '的', '是', '在', '了', '和', '与', '或', '等', '有', '为', '被', '把', '对',
    '从', '到', '给', '用', '以', '及', '如何', '怎么', '什么', '哪些', '哪个',
    '怎样', '请问', '能', '可以', '吗', '呢', '啊', '吧', '一个', '这个', '那个',
}

_TOKEN_RE = re.compile(r'[a-zA-Z0-9_.\-]+')


def tokenize(text: str) -> List[str]:
    """中文 jieba 分词 + 英文/数字/型号 token 提取，过滤停用词。"""
    tokens: List[str] = []
    # 英文单词、数字、型号（如 RTX-3060、err_code.404）整体保留
    tokens.extend(t.lower() for t in _TOKEN_RE.findall(text))
    try:
        import jieba
        tokens.extend(
            w for w in jieba.cut(text)
            if len(w.strip()) >= 2 and not _TOKEN_RE.fullmatch(w)
        )
    except ImportError:
        # 回退：2-gram 滑窗
        clean = re.sub(r'[^一-鿿]', '', text)
        tokens.extend(clean[i:i + 2] for i in range(len(clean) - 1))
    return [t for t in tokens if t not in _STOPWORDS and t.strip()]


class BM25Index:
    """对一组文档构建的 BM25 索引。文档以列表下标为 id。"""

    def __init__(self, documents: List[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_count = len(documents)
        self.doc_tokens: List[Counter] = []
        self.doc_lens: List[int] = []
        self.df: Dict[str, int] = {}

        for doc in documents:
            tokens = Counter(tokenize(doc))
            self.doc_tokens.append(tokens)
            self.doc_lens.append(sum(tokens.values()))
            for term in tokens:
                self.df[term] = self.df.get(term, 0) + 1

        self.avgdl = (sum(self.doc_lens) / self.doc_count) if self.doc_count else 0.0
        self.idf: Dict[str, float] = {
            term: math.log(1 + (self.doc_count - df + 0.5) / (df + 0.5))
            for term, df in self.df.items()
        }

    def search(self, query: str, top_k: int = 20) -> List[Tuple[int, float]]:
        """返回 [(doc_index, score)]，按得分降序；得分为 0 的文档不返回。"""
        if not self.doc_count:
            return []
        query_terms = tokenize(query)
        if not query_terms:
            return []

        scores = [0.0] * self.doc_count
        for term in query_terms:
            idf = self.idf.get(term)
            if idf is None:
                continue
            for i, tokens in enumerate(self.doc_tokens):
                tf = tokens.get(term, 0)
                if tf == 0:
                    continue
                dl = self.doc_lens[i]
                denom = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                scores[i] += idf * tf * (self.k1 + 1) / denom

        ranked = [(i, s) for i, s in enumerate(scores) if s > 0]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
