"""RAG 检索消融评测脚本。

对同一份测试集，跑多种检索配置并统计 Recall@K 与耗时：
1. dense       — 旧链路（向量 + 关键词加分）
2. hybrid      — Dense + BM25 → RRF（无精排）
3. hybrid_rr   — Dense + BM25 → RRF → Reranker（需 RERANKER_ENABLED=true）

测试集格式（JSONL，每行一条）：
    {"query": "上传图片有什么格式要求", "kb_type": "guide", "expect_file": "xxx.md", "expect_keyword": "10MB"}

- expect_file:    期望命中的文档名（Top-K 内任一结果的 file 匹配即算命中）
- expect_keyword: 期望出现在召回内容里的关键词（可选，二者满足其一即命中）

用法：
    python scripts/eval_retrieval.py data/test_data/retrieval_eval.jsonl --top-k 5
"""
import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402


def load_cases(path: Path):
    cases = []
    with path.open(encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                cases.append(json.loads(line))
    return cases


def hit(case, results):
    expect_file = case.get('expect_file')
    expect_kw = case.get('expect_keyword')
    for r in results:
        if expect_file and r.get('file') == expect_file:
            return True
        content = (r.get('content') or '') + (r.get('context') or '')
        if expect_kw and expect_kw in content:
            return True
    return False


def run_config(client, cases, mode, rerank, top_k):
    hits = 0
    latencies = []
    errors = 0
    for case in cases:
        payload = {
            'query': case['query'],
            'kb_type': case.get('kb_type', 'guide'),
            'top_k': top_k,
            'mode': mode,
            'rerank': rerank,
        }
        start = time.perf_counter()
        resp = client.post('/api/kb/search', json=payload)
        latencies.append((time.perf_counter() - start) * 1000)
        if resp.status_code != 200:
            errors += 1
            continue
        if hit(case, resp.get_json().get('results', [])):
            hits += 1

    latencies.sort()
    n = len(cases)
    p95 = latencies[int(len(latencies) * 0.95) - 1] if latencies else 0
    return {
        'recall': hits / n if n else 0,
        'hits': hits,
        'total': n,
        'errors': errors,
        'avg_ms': sum(latencies) / len(latencies) if latencies else 0,
        'p95_ms': p95,
    }


def main():
    parser = argparse.ArgumentParser(description='RAG 检索消融评测')
    parser.add_argument('dataset', help='JSONL 测试集路径')
    parser.add_argument('--top-k', type=int, default=5)
    args = parser.parse_args()

    cases = load_cases(Path(args.dataset))
    if not cases:
        print('测试集为空'); sys.exit(1)
    print(f'测试集: {len(cases)} 条, Top-K={args.top_k}\n')

    client = create_app().test_client()

    configs = [
        ('dense (旧链路)', 'dense', False),
        ('hybrid (Dense+BM25+RRF)', 'hybrid', False),
        ('hybrid+rerank', 'hybrid', True),
    ]

    print(f"{'配置':<28} {'Recall@' + str(args.top_k):<10} {'命中':<8} {'错误':<6} {'均耗时':<10} {'P95'}")
    print('-' * 75)
    for name, mode, rerank in configs:
        stats = run_config(client, cases, mode, rerank, args.top_k)
        print(f"{name:<28} {stats['recall']:>7.1%}   "
              f"{stats['hits']}/{stats['total']:<6} {stats['errors']:<6} "
              f"{stats['avg_ms']:>7.0f}ms  {stats['p95_ms']:>6.0f}ms")


if __name__ == '__main__':
    main()
