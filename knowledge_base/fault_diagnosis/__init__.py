"""
故障诊断知识库模块
提供基于 FAISS 的语义向量检索功能
"""
from .vector_store import (
    BGEEmbedding,
    FAISSVectorStore,
    FaultDiagnosisKnowledgeBase,
    build_knowledge_base
)

__all__ = [
    'BGEEmbedding',
    'FAISSVectorStore',
    'FaultDiagnosisKnowledgeBase',
    'build_knowledge_base'
]
