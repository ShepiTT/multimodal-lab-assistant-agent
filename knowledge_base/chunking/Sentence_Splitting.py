"""
基于句子的分块 (Sentence Splitting)
按句子边界进行切分，保持语义完整性
"""
import re
from typing import List, Dict, Any


class SentenceSplitter:
    """基于句子的文本切分器"""
    
    def __init__(self, max_chunk_size: int = 500, min_chunk_size: int = 100):
        """
        初始化切分器
        
        Args:
            max_chunk_size: 每个块的最大字符数
            min_chunk_size: 每个块的最小字符数
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        # 句子分隔符正则表达式
        self.sentence_pattern = re.compile(r'([。！？.!?]+[\s]*|[\n]+)')
    
    def _split_sentences(self, text: str) -> List[str]:
        """将文本切分为句子列表"""
        sentences = []
        parts = self.sentence_pattern.split(text)
        
        current_sentence = ""
        for i, part in enumerate(parts):
            if self.sentence_pattern.match(part):
                current_sentence += part
                if current_sentence.strip():
                    sentences.append(current_sentence.strip())
                current_sentence = ""
            else:
                current_sentence += part
        
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        return sentences
    
    def chunk(self, text: str) -> List[Dict[str, Any]]:
        """
        对文本进行基于句子的切分
        
        Args:
            text: 待切分的文本
            
        Returns:
            切分后的文本块列表
        """
        if not text or not text.strip():
            return []
        
        sentences = self._split_sentences(text)
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_id = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # 如果单个句子超过最大长度，需要强制切分
            if sentence_length > self.max_chunk_size:
                # 先保存当前块
                if current_chunk:
                    chunks.append({
                        'id': chunk_id,
                        'content': ' '.join(current_chunk),
                        'sentence_count': len(current_chunk),
                        'length': current_length
                    })
                    chunk_id += 1
                    current_chunk = []
                    current_length = 0
                
                # 强制切分长句子
                for i in range(0, sentence_length, self.max_chunk_size):
                    sub_sentence = sentence[i:i + self.max_chunk_size]
                    chunks.append({
                        'id': chunk_id,
                        'content': sub_sentence,
                        'sentence_count': 1,
                        'length': len(sub_sentence)
                    })
                    chunk_id += 1
                continue
            
            # 检查是否需要开始新块
            if current_length + sentence_length > self.max_chunk_size and current_chunk:
                chunks.append({
                    'id': chunk_id,
                    'content': ' '.join(current_chunk),
                    'sentence_count': len(current_chunk),
                    'length': current_length
                })
                chunk_id += 1
                current_chunk = []
                current_length = 0
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # 处理最后一个块
        if current_chunk:
            chunks.append({
                'id': chunk_id,
                'content': ' '.join(current_chunk),
                'sentence_count': len(current_chunk),
                'length': current_length
            })
        
        return chunks


def sentence_split(text: str, max_chunk_size: int = 500, min_chunk_size: int = 100) -> List[Dict[str, Any]]:
    """
    便捷函数：对文本进行基于句子的切分
    
    Args:
        text: 待切分的文本
        max_chunk_size: 每个块的最大字符数
        min_chunk_size: 每个块的最小字符数
        
    Returns:
        切分后的文本块列表
    """
    splitter = SentenceSplitter(max_chunk_size=max_chunk_size, min_chunk_size=min_chunk_size)
    return splitter.chunk(text)


if __name__ == "__main__":
    # 测试代码
    test_text = """
    人工智能是计算机科学的一个分支。它企图了解智能的实质。该领域的研究包括机器人、语言识别、图像识别等。
    人工智能从诞生以来，理论和技术日益成熟！应用领域也不断扩大？未来人工智能将会是人类智慧的"容器"。
    """
    
    chunks = sentence_split(test_text, max_chunk_size=100)
    for chunk in chunks:
        print(f"Chunk {chunk['id']}: {chunk['content'][:50]}... (句子数: {chunk['sentence_count']})")
