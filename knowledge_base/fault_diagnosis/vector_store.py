"""
向量知识库
基于 BGE-M3 模型进行文本向量化，使用 FAISS 构建高效语义检索
"""
import os
import pickle
import logging
from typing import List, Dict, Any
from pathlib import Path

import numpy as np

# 设置环境变量
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # 使用第一块 GPU

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BGEEmbedding:
    """BGE-M3 向量化模型封装"""
    
    _instance = None
    
    def __new__(cls, model_path: str = None, device: str = "cpu"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, model_path: str = None, device: str = None):
        if self._initialized:
            return
        
        # 自动检测 GPU
        if device is None:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            if device == "cuda":
                logger.info(f"检测到 GPU: {torch.cuda.get_device_name(0)}")
        
        self.device = device
        self.model = None
        # 优先使用本地缓存的模型路径
        local_cache_path = os.path.expanduser("~/.cache/huggingface/hub/models--BAAI--bge-base-zh-v1.5/snapshots")
        if model_path:
            self.model_path = model_path
        elif os.path.exists(local_cache_path):
            # 查找包含 modules.json 的完整 snapshot（sentence-transformers 格式）
            snapshots = [d for d in os.listdir(local_cache_path) if os.path.isdir(os.path.join(local_cache_path, d))]
            valid_snapshot = None
            for snap in snapshots:
                snap_path = os.path.join(local_cache_path, snap)
                # 检查是否包含 modules.json（sentence-transformers 模型必需文件）
                if os.path.exists(os.path.join(snap_path, "modules.json")):
                    valid_snapshot = snap_path
                    break
            if valid_snapshot:
                self.model_path = valid_snapshot
                logger.info(f"使用本地缓存模型: {self.model_path}")
            else:
                self.model_path = "BAAI/bge-base-zh-v1.5"
        else:
            self.model_path = "BAAI/bge-base-zh-v1.5"
        self._load_model()
        self._initialized = True
    
    def _load_model(self):
        """使用 sentence-transformers 加载模型"""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"正在加载模型: {self.model_path}")
            self.model = SentenceTransformer(self.model_path, device=self.device)
            logger.info("模型加载成功")
        except Exception as e:
            logger.error(f"加载失败: {e}")
            raise RuntimeError("无法加载向量化模型")
    
    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """对文本进行向量化编码"""
        if not texts:
            return np.array([])
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True
        )
        return np.array(embeddings).astype('float32')


class FAISSVectorStore:
    """FAISS 向量存储和检索"""
    
    def __init__(self, embedding_dim: int = 1024):
        import faiss
        
        self.embedding_dim = embedding_dim
        self.index = faiss.IndexFlatIP(embedding_dim)
        self.documents = []
        self.metadata = []
        
        logger.info(f"创建 FAISS 索引，维度: {embedding_dim}")
    
    def add(self, embeddings: np.ndarray, documents: List[str], metadata: List[Dict] = None):
        """添加向量到索引"""
        import faiss
        
        if len(embeddings) == 0:
            return
        
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        self.documents.extend(documents)
        self.metadata.extend(metadata or [{} for _ in documents])
        
        logger.info(f"添加 {len(documents)} 个文档，总数: {self.index.ntotal}")
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索最相似的文档"""
        import faiss
        
        if self.index.ntotal == 0:
            return []
        
        query = query_embedding.reshape(1, -1).astype('float32')
        faiss.normalize_L2(query)
        
        scores, indices = self.index.search(query, min(top_k, self.index.ntotal))
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                results.append({
                    'document': self.documents[idx],
                    'metadata': self.metadata[idx],
                    'score': float(score),
                    'index': int(idx)
                })
        return results
    
    def save(self, save_dir: str):
        """保存索引（使用 pickle 序列化 FAISS 索引）"""
        import faiss
        
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        
        # 使用 faiss 的序列化方法转为 bytes，再用 pickle 保存
        index_bytes = faiss.serialize_index(self.index)
        
        data = {
            'index_bytes': index_bytes,
            'documents': self.documents,
            'metadata': self.metadata,
            'embedding_dim': self.embedding_dim
        }
        
        save_file = save_path / "index.pkl"
        with open(save_file, 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"索引已保存到: {save_file}")
    
    def load(self, save_dir: str):
        """加载索引"""
        import faiss
        
        save_file = Path(save_dir) / "index.pkl"
        
        with open(save_file, 'rb') as f:
            data = pickle.load(f)
        
        self.index = faiss.deserialize_index(data['index_bytes'])
        self.documents = data['documents']
        self.metadata = data['metadata']
        self.embedding_dim = data['embedding_dim']
        
        logger.info(f"索引已加载，文档数: {self.index.ntotal}")


class FaultDiagnosisKnowledgeBase:
    """知识库"""
    
    def __init__(self, data_dir: str = None, model_path: str = None,
                 chunk_method: str = "semantic", chunk_size: int = 500, device: str = None):
        self.data_dir = data_dir or os.path.dirname(os.path.abspath(__file__))
        self.chunk_method = chunk_method
        self.chunk_size = chunk_size
        self.device = device
        self.model_path = model_path
        
        self.embedder = None
        self.vector_store = None
        self.index_dir = os.path.join(self.data_dir, "index")
    
    def _init_embedder(self):
        if self.embedder is None:
            self.embedder = BGEEmbedding(model_path=self.model_path, device=self.device)
    
    def _init_vector_store(self, embedding_dim: int = 1024):
        if self.vector_store is None:
            self.vector_store = FAISSVectorStore(embedding_dim=embedding_dim)
    
    def _get_chunker(self):
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        if self.chunk_method == "fixed" or self.chunk_method == "fixed_size":
            from chunking.Fixed_size_Chunking import FixedSizeChunker
            return FixedSizeChunker(chunk_size=self.chunk_size, overlap=100)
        elif self.chunk_method == "sentence":
            from chunking.Sentence_Splitting import SentenceSplitter
            return SentenceSplitter(max_chunk_size=self.chunk_size)
        elif self.chunk_method == "recursive":
            from chunking.Recursive_Chunking import RecursiveChunker
            return RecursiveChunker(chunk_size=self.chunk_size)
        elif self.chunk_method == "hybrid":
            from chunking.Hybrid_Chunking import HybridChunker
            # HybridChunker 需要特殊处理，使用 chunk_to_dicts 方法
            class HybridChunkerWrapper:
                def __init__(self, chunk_size):
                    self._chunker = HybridChunker(chunk_size=chunk_size)
                def chunk(self, text):
                    return self._chunker.chunk_to_dicts(text)
            return HybridChunkerWrapper(self.chunk_size)
        elif self.chunk_method == "smart":
            from chunking.Smart_Chunking import SmartChunker
            # 智能切分：自动检测文档类型，支持重叠
            return SmartChunker(
                chunk_size=self.chunk_size,
                overlap=50,  # 50字符重叠，保持上下文
                min_chunk_size=100,
                respect_sentences=True,
                preserve_code_blocks=True
            )
        else:  # semantic 或其他默认使用语义分块
            from chunking.Semantic_Chunking import SemanticChunker
            return SemanticChunker(max_chunk_size=self.chunk_size)
    
    def _read_document(self, file_path: str) -> str:
        """读取文档内容"""
        try:
            import sys
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            from parsing_service import parse_file
            result = parse_file(file_path)
            
            if result['success'] and result['type'] == 'text':
                return result['content']
            return ""
        except Exception as e:
            logger.warning(f"解析失败: {e}，使用备用方法")
            return self._fallback_read(file_path)
    
    def _fallback_read(self, file_path: str) -> str:
        """备用读取方法"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in {'.md', '.txt', '.html', '.htm'}:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except:
                with open(file_path, 'r', encoding='gbk') as f:
                    return f.read()
        elif ext == '.docx':
            try:
                from docx import Document
                doc = Document(file_path)
                return '\n'.join([p.text for p in doc.paragraphs])
            except:
                return ""
        elif ext == '.pdf':
            try:
                import fitz
                doc = fitz.open(file_path)
                return ''.join([page.get_text() for page in doc])
            except:
                return ""
        return ""
    
    def build_index(self, source_dir: str = None, enabled_files: List[str] = None):
        """构建知识库索引
        
        Args:
            source_dir: 源文件目录
            enabled_files: 启用的文件名列表，为 None 时处理所有文件
        """
        import json
        from datetime import datetime
        
        source_dir = source_dir or os.path.join(self.data_dir, "data")
        
        if not os.path.exists(source_dir):
            raise FileNotFoundError(f"目录不存在: {source_dir}")
        
        # 创建日志目录
        log_dir = os.path.join(self.data_dir, "log")
        os.makedirs(log_dir, exist_ok=True)
        
        # 日志文件名带时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"build_{timestamp}.log")
        chunks_file = os.path.join(log_dir, f"chunks_{timestamp}.json")
        
        # 日志记录函数
        def log(msg: str, level: str = "INFO"):
            log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] [{level}] {msg}"
            logger.info(msg)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_msg + '\n')
        
        log("=" * 60)
        log("知识库索引构建开始")
        log("=" * 60)
        log(f"源目录: {source_dir}")
        log(f"切分方法: {self.chunk_method}")
        log(f"切分大小: {self.chunk_size}")
        
        if enabled_files:
            log(f"启用的文件: {enabled_files}")
        
        chunker = self._get_chunker()
        all_chunks = []
        all_metadata = []
        chunks_detail = []  # 用于保存详细切分结果
        
        # 统计信息
        stats = {
            'total_files': 0,
            'processed_files': 0,
            'skipped_files': 0,
            'total_chunks': 0,
            'total_chars': 0,
            'files': []
        }
        
        log("-" * 40)
        log("开始处理文件")
        log("-" * 40)
        
        for filename in os.listdir(source_dir):
            if filename == 'text.json':
                continue
            
            stats['total_files'] += 1
            
            # 如果指定了启用文件列表，只处理列表中的文件
            if enabled_files is not None and filename not in enabled_files:
                log(f"跳过未启用的文件: {filename}", "SKIP")
                stats['skipped_files'] += 1
                continue
            
            file_path = os.path.join(source_dir, filename)
            if not os.path.isfile(file_path):
                continue
            
            log(f"\n处理文件: {filename}")
            
            # 读取文档
            content = self._read_document(file_path)
            if not content:
                log(f"  文件内容为空，跳过", "WARN")
                stats['skipped_files'] += 1
                continue
            
            content_len = len(content)
            log(f"  文档长度: {content_len} 字符")
            
            # 切分文档
            chunks = chunker.chunk(content)
            chunk_count = len(chunks)
            log(f"  切分结果: {chunk_count} 个块")
            
            file_stat = {
                'filename': filename,
                'content_length': content_len,
                'chunk_count': chunk_count,
                'chunks': []
            }
            
            # 记录每个切分块的详细信息
            for i, chunk in enumerate(chunks):
                chunk_content = chunk.get('content', '')
                if not chunk_content.strip():
                    continue
                
                chunk_len = len(chunk_content)
                chunk_title = chunk.get('title', '')
                chunk_preview = chunk_content[:100].replace('\n', ' ')
                
                log(f"    块 {i}: 长度={chunk_len}, 标题=\"{chunk_title}\"")
                log(f"         预览: {chunk_preview}...")
                
                all_chunks.append(chunk_content)
                all_metadata.append({
                    'source': filename,
                    'chunk_id': chunk.get('id', 0),
                    'title': chunk_title,
                    'length': chunk_len
                })
                
                # 保存详细信息
                file_stat['chunks'].append({
                    'id': i,
                    'title': chunk_title,
                    'length': chunk_len,
                    'content': chunk_content
                })
                
                stats['total_chars'] += chunk_len
            
            stats['processed_files'] += 1
            stats['total_chunks'] += chunk_count
            stats['files'].append({
                'filename': filename,
                'content_length': content_len,
                'chunk_count': chunk_count
            })
            chunks_detail.append(file_stat)
        
        log("-" * 40)
        log("文件处理完成")
        log("-" * 40)
        
        if not all_chunks:
            log("没有有效文档内容，构建终止", "ERROR")
            return
        
        log(f"\n统计信息:")
        log(f"  总文件数: {stats['total_files']}")
        log(f"  已处理: {stats['processed_files']}")
        log(f"  已跳过: {stats['skipped_files']}")
        log(f"  总切分块: {stats['total_chunks']}")
        log(f"  总字符数: {stats['total_chars']}")
        
        # 保存切分详情到 JSON
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump({
                'build_time': timestamp,
                'chunk_method': self.chunk_method,
                'chunk_size': self.chunk_size,
                'stats': stats,
                'files': chunks_detail
            }, f, ensure_ascii=False, indent=2)
        log(f"\n切分详情已保存: {chunks_file}")
        
        # 向量化
        log("-" * 40)
        log("开始向量化")
        log("-" * 40)
        
        self._init_embedder()
        log(f"向量化模型: {self.embedder.model_path}")
        log(f"设备: {self.embedder.device}")
        log(f"待向量化文本块: {len(all_chunks)} 个")
        
        embeddings = self.embedder.encode(all_chunks, batch_size=16)
        log(f"向量化完成，维度: {embeddings.shape}")
        
        # 构建索引
        log("-" * 40)
        log("构建 FAISS 索引")
        log("-" * 40)
        
        self._init_vector_store(embedding_dim=embeddings.shape[1])
        self.vector_store.add(embeddings, all_chunks, all_metadata)
        self.vector_store.save(self.index_dir)
        
        log(f"索引已保存: {self.index_dir}")
        
        log("=" * 60)
        log("知识库索引构建完成！")
        log(f"日志文件: {log_file}")
        log("=" * 60)
        
        return {
            'success': True,
            'log_file': log_file,
            'chunks_file': chunks_file,
            'stats': stats
        }
    
    def load_index(self):
        """加载已有索引"""
        index_file = os.path.join(self.index_dir, "index.pkl")
        if not os.path.exists(index_file):
            raise FileNotFoundError(f"索引不存在: {index_file}")
        
        self._init_embedder()
        test_emb = self.embedder.encode(["test"])
        self._init_vector_store(embedding_dim=test_emb.shape[1])
        self.vector_store.load(self.index_dir)
    
    def _keyword_boost(self, query: str, documents: List[str], base_scores: List[float], boost_weight: float = 0.3) -> List[float]:
        """
        关键词匹配加分（增强版）
        - 支持同义词扩展
        - 支持中文分词（jieba 或简单规则）
        - 对包含查询关键词的文档进行加分
        """
        import re
        
        # 同义词映射表
        synonyms = {
            '图片': ['图像', '照片', '图'],
            '图像': ['图片', '照片', '图'],
            '格式': ['类型', '形式'],
            '上传': ['传输', '导入'],
            '大小': ['尺寸', '容量', '限制'],
            '要求': ['规范', '规定', '限制', '条件'],
            '视频': ['影片', '录像'],
            '语音': ['音频', '声音', '录音'],
            '文档': ['文件', '资料'],
            '文件': ['文档', '资料'],
        }
        
        # 停用词
        stopwords = {'的', '是', '在', '了', '和', '与', '或', '等', '有', '为', '被', '把', '对', '从', '到', '给', '用', '以', '及', '如何', '怎么', '什么', '哪些', '哪个', '怎样', '请问', '能', '可以', '吗', '呢', '啊', '吧'}
        
        # 尝试使用 jieba 分词
        try:
            import jieba
            words = list(jieba.cut(query))
        except ImportError:
            # 备用：简单按标点和空格分割 + 滑动窗口提取
            words = re.split(r'[，。？！、\s]+', query)
            # 添加滑动窗口提取的词（2-4字）
            extra_words = []
            clean_query = re.sub(r'[，。？！、\s]+', '', query)
            for length in [2, 3, 4]:
                for i in range(len(clean_query) - length + 1):
                    extra_words.append(clean_query[i:i+length])
            words.extend(extra_words)
        
        # 过滤关键词
        keywords = [w for w in words if w and len(w) >= 2 and w not in stopwords]
        
        # 扩展同义词
        expanded_keywords = set(keywords)
        for kw in keywords:
            if kw in synonyms:
                expanded_keywords.update(synonyms[kw])
        
        if not expanded_keywords:
            return base_scores
        
        boosted_scores = []
        for doc, base_score in zip(documents, base_scores):
            doc_lower = doc.lower()
            
            # 计算关键词匹配度
            match_count = 0
            matched_keywords = []
            for kw in expanded_keywords:
                if kw.lower() in doc_lower:
                    match_count += 1
                    matched_keywords.append(kw)
            
            # 关键词匹配加分
            if match_count > 0:
                # 匹配比例
                keyword_score = match_count / len(expanded_keywords)
                # 原始关键词匹配额外加分
                original_match = sum(1 for kw in keywords if kw.lower() in doc_lower)
                original_bonus = original_match / len(keywords) * 0.1 if keywords else 0
                
                # 混合得分
                final_score = base_score * (1 - boost_weight) + keyword_score * boost_weight + original_bonus
            else:
                final_score = base_score
            
            boosted_scores.append(final_score)
        
        return boosted_scores
    
    def search(self, query: str, top_k: int = 5, use_keyword_boost: bool = True) -> List[Dict[str, Any]]:
        """
        搜索相关文档（混合检索）
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            use_keyword_boost: 是否启用关键词加分
        """
        if self.vector_store is None or self.vector_store.index.ntotal == 0:
            logger.warning("索引为空")
            return []
        
        # 先获取更多候选结果
        candidate_k = min(top_k * 3, self.vector_store.index.ntotal)
        query_embedding = self.embedder.encode([query])[0]
        candidates = self.vector_store.search(query_embedding, top_k=candidate_k)
        
        if not use_keyword_boost:
            return candidates[:top_k]
        
        # 关键词加分重排序
        documents = [c['document'] for c in candidates]
        base_scores = [c['score'] for c in candidates]
        boosted_scores = self._keyword_boost(query, documents, base_scores)
        
        # 按加分后的得分重排序
        for i, candidate in enumerate(candidates):
            candidate['boosted_score'] = boosted_scores[i]
        
        candidates.sort(key=lambda x: x['boosted_score'], reverse=True)
        
        # 返回 top_k 结果，使用加分后的得分
        results = []
        for c in candidates[:top_k]:
            results.append({
                'document': c['document'],
                'metadata': c['metadata'],
                'score': c['boosted_score'],  # 使用加分后的得分
                'original_score': c['score'],  # 保留原始语义得分
                'index': c['index']
            })
        
        return results


def build_knowledge_base(data_dir: str = None, model_path: str = None,
                         chunk_method: str = "semantic", chunk_size: int = 500, device: str = None):
    """便捷函数：构建知识库"""
    kb = FaultDiagnosisKnowledgeBase(
        data_dir=data_dir, model_path=model_path,
        chunk_method=chunk_method, chunk_size=chunk_size, device=device
    )
    kb.build_index()
    return kb
