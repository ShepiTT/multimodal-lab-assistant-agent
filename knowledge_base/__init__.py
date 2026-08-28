"""
知识库模块
提供基于 FAISS 的语义向量检索功能

支持的知识库类型:
- operating_instructions: 操作指导
- fault_diagnosis: 故障诊断
- safety_regulations: 安全规范
- code_debug: 代码调试
"""
from .fault_diagnosis.vector_store import (
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
