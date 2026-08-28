"""
文本切分算法模块
提供多种文本切分策略用于知识库构建

支持的分块策略：
1. 固定大小分块 (Fixed-size Chunking) - 按固定字符数切分
2. 基于句子的分块 (Sentence Splitting) - 按句子边界切分
3. 递归字符分块 (Recursive Character Text Splitting) - 按分隔符优先级递归切分
4. 基于文档结构的分块 (Semantic Chunking) - 基于标题、段落等结构切分
5. 混合分块 (Hybrid Chunking) - 结合文档结构和递归分割，保护代码块完整性
6. 智能分块 (Smart Chunking) - 自动检测文档类型，选择最佳策略，支持重叠
"""
from .Fixed_size_Chunking import FixedSizeChunker, fixed_size_chunk
from .Sentence_Splitting import SentenceSplitter, sentence_split
from .Recursive_Chunking import RecursiveChunker, recursive_chunk
from .Semantic_Chunking import SemanticChunker, semantic_chunk
from .Hybrid_Chunking import HybridChunker, hybrid_chunk, Chunk
from .Smart_Chunking import SmartChunker, smart_chunk

__all__ = [
    # 固定大小分块
    'FixedSizeChunker',
    'fixed_size_chunk',
    # 基于句子的分块
    'SentenceSplitter', 
    'sentence_split',
    # 递归字符分块
    'RecursiveChunker',
    'recursive_chunk',
    # 基于文档结构的分块（语义分块）
    'SemanticChunker',
    'semantic_chunk',
    # 混合分块
    'HybridChunker',
    'hybrid_chunk',
    'Chunk',
    # 智能分块（推荐）
    'SmartChunker',
    'smart_chunk',
]
