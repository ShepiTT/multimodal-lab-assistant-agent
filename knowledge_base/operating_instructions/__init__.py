"""
操作指导知识库模块
"""
from knowledge_base.fault_diagnosis.vector_store import (
    BGEEmbedding,
    FAISSVectorStore,
    FaultDiagnosisKnowledgeBase as KnowledgeBase,
    build_knowledge_base
)

__all__ = [
    'BGEEmbedding',
    'FAISSVectorStore',
    'KnowledgeBase',
    'build_knowledge_base'
]
