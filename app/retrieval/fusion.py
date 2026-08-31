"""RRF（Reciprocal Rank Fusion）融合多路召回结果。

RRF 只看排名不看原始得分，天然规避 Dense 余弦相似度与 BM25 得分
量纲不可比的问题。score(d) = Σ 1 / (k + rank_i(d))，k 常取 60。
"""
from typing import Dict, List, Sequence, Tuple


def rrf_fuse(rankings: Sequence[Sequence[int]], k: int = 60,
             weights: Sequence[float] = None) -> List[Tuple[int, float]]:
    """融合多路召回的文档 id 排名列表。

    Args:
        rankings: 每路召回的文档 id 列表（按各自相关度降序）
        k: RRF 平滑常数，越大各路排名差异被压得越平
        weights: 每路权重，默认全 1

    Returns:
        [(doc_id, rrf_score)]，按融合得分降序
    """
    if weights is None:
        weights = [1.0] * len(rankings)

    scores: Dict[int, float] = {}
    for ranking, weight in zip(rankings, weights):
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + weight / (k + rank + 1)

    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return fused
