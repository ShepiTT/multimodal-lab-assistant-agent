"""
递归字符分块 (Recursive Character Text Splitting)
按分隔符优先级递归分割文本，在保持语义结构的同时控制块大小
"""
from typing import List, Dict, Any, Optional


class RecursiveChunker:
    """递归字符文本切分器"""
    
    def __init__(
        self, 
        chunk_size: int = 500, 
        separators: Optional[List[str]] = None
    ):
        """
        初始化切分器
        
        Args:
            chunk_size: 每个块的最大字符数
            separators: 分隔符优先级列表，从高到低
        """
        self.chunk_size = chunk_size
        # 默认分隔符优先级：段落 > 换行 > 句子 > 空格 > 字符
        self.separators = separators or [
            "\n\n",      # 段落分隔
            "\n",        # 换行符
            "。", "！", "？",  # 中文句子结束符
            ".", "!", "?",    # 英文句子结束符
            "；", ";",        # 分号
            "，", ",",        # 逗号
            " ",              # 空格
            ""                # 字符级别（最后兜底）
        ]
    
    def _split_by_separator(self, text: str, separator: str) -> List[str]:
        """按指定分隔符切分文本"""
        if separator == "":
            # 字符级别切分
            return list(text)
        
        parts = text.split(separator)
        # 保留分隔符（附加到前一个部分）
        result = []
        for i, part in enumerate(parts):
            if i < len(parts) - 1:
                result.append(part + separator)
            elif part:  # 最后一个部分不加分隔符
                result.append(part)
        return result
    
    def _recursive_split(self, text: str, separator_index: int = 0) -> List[str]:
        """递归切分文本"""
        # 如果文本已经足够小，直接返回
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []
        
        # 如果已经用完所有分隔符，强制按字符切分
        if separator_index >= len(self.separators):
            chunks = []
            for i in range(0, len(text), self.chunk_size):
                chunk = text[i:i + self.chunk_size]
                if chunk.strip():
                    chunks.append(chunk)
            return chunks
        
        separator = self.separators[separator_index]
        parts = self._split_by_separator(text, separator)
        
        # 如果当前分隔符无法有效切分（只有一个部分），尝试下一个分隔符
        if len(parts) <= 1:
            return self._recursive_split(text, separator_index + 1)
        
        # 合并小块，确保每个块不超过 chunk_size
        chunks = []
        current_chunk = ""
        
        for part in parts:
            # 如果单个部分就超过 chunk_size，需要递归处理
            if len(part) > self.chunk_size:
                # 先保存当前累积的内容
                if current_chunk.strip():
                    chunks.append(current_chunk)
                    current_chunk = ""
                # 递归处理超大部分
                sub_chunks = self._recursive_split(part, separator_index + 1)
                chunks.extend(sub_chunks)
            elif len(current_chunk) + len(part) > self.chunk_size:
                # 当前块加上新部分会超过限制，保存当前块
                if current_chunk.strip():
                    chunks.append(current_chunk)
                current_chunk = part
            else:
                # 继续累积
                current_chunk += part
        
        # 处理最后剩余的内容
        if current_chunk.strip():
            chunks.append(current_chunk)
        
        return chunks
    
    def chunk(self, text: str) -> List[Dict[str, Any]]:
        """
        对文本进行递归字符切分
        
        Args:
            text: 待切分的文本
            
        Returns:
            切分后的文本块列表，每个块包含内容和元数据
        """
        if not text or not text.strip():
            return []
        
        raw_chunks = self._recursive_split(text)
        
        chunks = []
        for i, content in enumerate(raw_chunks):
            content = content.strip()
            if content:
                chunks.append({
                    'id': i,
                    'content': content,
                    'length': len(content)
                })
        
        return chunks


def recursive_chunk(
    text: str, 
    chunk_size: int = 500, 
    separators: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    便捷函数：对文本进行递归字符切分
    
    Args:
        text: 待切分的文本
        chunk_size: 每个块的最大字符数
        separators: 分隔符优先级列表
        
    Returns:
        切分后的文本块列表
    """
    chunker = RecursiveChunker(chunk_size=chunk_size, separators=separators)
    return chunker.chunk(text)


if __name__ == "__main__":
    # 测试代码
    test_text = """
人工智能（Artificial Intelligence，简称AI）是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。

该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。人工智能从诞生以来，理论和技术日益成熟，应用领域也不断扩大。

可以设想，未来人工智能带来的科技产品，将会是人类智慧的"容器"。人工智能可以对人的意识、思维的信息过程的模拟。人工智能不是人的智能，但能像人那样思考、也可能超过人的智能。
"""
    
    print("=== 递归字符分块测试 ===")
    chunks = recursive_chunk(test_text, chunk_size=150)
    for chunk in chunks:
        print(f"\nChunk {chunk['id']} (长度: {chunk['length']}):")
        print(f"  {chunk['content'][:80]}...")
