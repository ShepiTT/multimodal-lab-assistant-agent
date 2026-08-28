"""
固定大小分块 (Fixed-size Chunking)
将文档按固定字符数或token数进行切分，支持重叠窗口
"""
from typing import List, Dict, Any


class FixedSizeChunker:
    """固定大小文本切分器"""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 100):
        """
        初始化切分器
        
        Args:
            chunk_size: 每个块的最大字符数
            overlap: 相邻块之间的重叠字符数
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk(self, text: str) -> List[Dict[str, Any]]:
        """
        对文本进行固定大小切分
        
        Args:
            text: 待切分的文本
            
        Returns:
            切分后的文本块列表，每个块包含内容和元数据
        """
        if not text or not text.strip():
            return []
        
        chunks = []
        start = 0
        chunk_id = 0
        text_length = len(text)
        
        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            chunk_text = text[start:end]
            
            # 如果不是最后一块，尝试在句子边界处切分
            if end < text_length:
                # 寻找最近的句子结束符
                for sep in ['。', '！', '？', '\n', '.', '!', '?']:
                    last_sep = chunk_text.rfind(sep)
                    if last_sep > self.chunk_size * 0.5:  # 至少保留一半内容
                        end = start + last_sep + 1
                        chunk_text = text[start:end]
                        break
            
            chunks.append({
                'id': chunk_id,
                'content': chunk_text.strip(),
                'start': start,
                'end': end,
                'length': len(chunk_text.strip())
            })
            
            chunk_id += 1
            # 下一块的起始位置，考虑重叠
            start = end - self.overlap if end < text_length else text_length
        
        return chunks


def fixed_size_chunk(text: str, chunk_size: int = 500, overlap: int = 100) -> List[Dict[str, Any]]:
    """
    便捷函数：对文本进行固定大小切分
    
    Args:
        text: 待切分的文本
        chunk_size: 每个块的最大字符数
        overlap: 相邻块之间的重叠字符数
        
    Returns:
        切分后的文本块列表
    """
    chunker = FixedSizeChunker(chunk_size=chunk_size, overlap=overlap)
    return chunker.chunk(text)


if __name__ == "__main__":
    # 测试代码
    test_text = """
    人工智能（Artificial Intelligence，简称AI）是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
    该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。人工智能从诞生以来，理论和技术日益成熟，应用领域也不断扩大。
    可以设想，未来人工智能带来的科技产品，将会是人类智慧的"容器"。人工智能可以对人的意识、思维的信息过程的模拟。
    """
    
    chunks = fixed_size_chunk(test_text, chunk_size=100, overlap=20)
    for chunk in chunks:
        print(f"Chunk {chunk['id']}: {chunk['content'][:50]}... (长度: {chunk['length']})")
