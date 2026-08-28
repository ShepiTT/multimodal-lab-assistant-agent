"""
智能分块 (Smart Chunking)
自动检测文档类型，选择最佳切分策略，并支持重叠机制

特点：
1. 自动识别 Markdown、代码、纯文本等文档类型
2. 根据文档类型选择最佳切分策略
3. 支持重叠窗口，保持上下文连贯性
4. 优化中文文本的句子边界检测
5. 保护代码块、表格等特殊结构的完整性
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ChunkResult:
    """切分结果"""
    id: int
    content: str
    length: int
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'content': self.content,
            'length': self.length,
            **self.metadata
        }


class SmartChunker:
    """智能文本切分器"""
    
    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 50,
        min_chunk_size: int = 100,
        respect_sentences: bool = True,
        preserve_code_blocks: bool = True
    ):
        """
        初始化智能切分器
        
        Args:
            chunk_size: 目标块大小（字符数）
            overlap: 重叠字符数，用于保持上下文连贯
            min_chunk_size: 最小块大小，避免产生过小的块
            respect_sentences: 是否尊重句子边界
            preserve_code_blocks: 是否保护代码块完整性
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size
        self.respect_sentences = respect_sentences
        self.preserve_code_blocks = preserve_code_blocks
        
        # 中英文句子结束符
        self.sentence_endings = re.compile(r'([。！？.!?]+[\s]*|[\n]{2,})')
        # Markdown 标题
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        # 代码块
        self.code_block_pattern = re.compile(r'(```[\s\S]*?```|~~~[\s\S]*?~~~)', re.MULTILINE)
        # 表格行
        self.table_pattern = re.compile(r'^\|.*\|$', re.MULTILINE)
    
    def _detect_doc_type(self, text: str) -> str:
        """检测文档类型"""
        # 检查是否有 Markdown 标题
        has_headings = bool(self.heading_pattern.search(text))
        # 检查是否有代码块
        has_code_blocks = bool(self.code_block_pattern.search(text))
        # 检查是否有表格
        has_tables = bool(self.table_pattern.search(text))
        
        if has_headings or has_code_blocks:
            return 'markdown'
        elif has_tables:
            return 'structured'
        else:
            return 'plain'
    
    def _extract_code_blocks(self, text: str) -> Tuple[str, List[Tuple[str, int, int]]]:
        """提取代码块，返回处理后的文本和代码块位置"""
        code_blocks = []
        placeholder_text = text
        
        for i, match in enumerate(self.code_block_pattern.finditer(text)):
            placeholder = f"__CODE_BLOCK_{i}__"
            code_blocks.append((match.group(), match.start(), match.end(), placeholder))
        
        # 从后往前替换，避免位置偏移
        for code, start, end, placeholder in reversed(code_blocks):
            placeholder_text = placeholder_text[:start] + placeholder + placeholder_text[end:]
        
        return placeholder_text, code_blocks
    
    def _restore_code_blocks(self, chunks: List[str], code_blocks: List[Tuple]) -> List[str]:
        """恢复代码块"""
        restored = []
        for chunk in chunks:
            for code, _, _, placeholder in code_blocks:
                chunk = chunk.replace(placeholder, code)
            restored.append(chunk)
        return restored
    
    def _find_sentence_boundary(self, text: str, target_pos: int, search_range: int = 100) -> int:
        """在目标位置附近找到最佳句子边界"""
        if not self.respect_sentences:
            return target_pos
        
        # 搜索范围
        start = max(0, target_pos - search_range)
        end = min(len(text), target_pos + search_range)
        search_text = text[start:end]
        
        # 找到所有句子结束位置
        boundaries = []
        for match in self.sentence_endings.finditer(search_text):
            abs_pos = start + match.end()
            boundaries.append(abs_pos)
        
        # 也考虑换行符作为边界
        for i, char in enumerate(search_text):
            if char == '\n':
                abs_pos = start + i + 1
                if abs_pos not in boundaries:
                    boundaries.append(abs_pos)
        
        if not boundaries:
            return target_pos
        
        # 找到最接近目标位置的边界
        best_boundary = min(boundaries, key=lambda x: abs(x - target_pos))
        
        # 如果边界太远，就用原位置
        if abs(best_boundary - target_pos) > search_range:
            return target_pos
        
        return best_boundary
    
    def _split_by_headings(self, text: str) -> List[Dict[str, Any]]:
        """按 Markdown 标题切分"""
        sections = []
        current_section = {'title': '', 'level': 0, 'content': [], 'start': 0}
        
        lines = text.split('\n')
        line_pos = 0
        
        for line in lines:
            heading_match = self.heading_pattern.match(line)
            if heading_match:
                # 保存当前 section
                if current_section['content']:
                    current_section['text'] = '\n'.join(current_section['content'])
                    sections.append(current_section)
                
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                current_section = {
                    'title': title,
                    'level': level,
                    'content': [line],
                    'start': line_pos
                }
            else:
                current_section['content'].append(line)
            
            line_pos += len(line) + 1
        
        # 保存最后一个 section
        if current_section['content']:
            current_section['text'] = '\n'.join(current_section['content'])
            sections.append(current_section)
        
        return sections
    
    def _split_large_section(self, text: str, title: str = '') -> List[str]:
        """将大段文本切分为合适大小的块"""
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            # 计算结束位置
            end = start + self.chunk_size
            
            if end >= len(text):
                # 最后一块
                chunk = text[start:]
                if chunk.strip():
                    chunks.append(chunk)
                break
            
            # 找到最佳切分点（在句子边界）
            end = self._find_sentence_boundary(text, end)
            
            # 确保至少前进一定距离，避免死循环
            if end <= start:
                end = start + self.chunk_size
            
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            
            # 下一块的起始位置，考虑重叠
            # 重叠起点应该从当前块的末尾往前 overlap 个字符
            next_start = end - self.overlap
            # 确保至少前进 chunk_size 的一半，避免过多重叠
            min_advance = max(self.chunk_size // 2, 100)
            start = max(start + min_advance, next_start)
        
        return chunks
    
    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        对文本进行智能切分
        
        Args:
            text: 待切分的文本
            metadata: 附加元数据
            
        Returns:
            切分后的块列表
        """
        if not text or not text.strip():
            return []
        
        base_metadata = metadata or {}
        doc_type = self._detect_doc_type(text)
        
        # 提取并保护代码块
        if self.preserve_code_blocks:
            processed_text, code_blocks = self._extract_code_blocks(text)
        else:
            processed_text = text
            code_blocks = []
        
        chunks = []
        chunk_id = 0
        
        if doc_type == 'markdown':
            # Markdown 文档：先按标题切分，再处理大段
            sections = self._split_by_headings(processed_text)
            
            for section in sections:
                section_text = section.get('text', '')
                section_title = section.get('title', '')
                section_level = section.get('level', 0)
                
                if len(section_text) > self.chunk_size:
                    # 大段需要进一步切分
                    sub_chunks = self._split_large_section(section_text, section_title)
                    for i, sub_chunk in enumerate(sub_chunks):
                        if self.preserve_code_blocks:
                            sub_chunk = self._restore_code_blocks([sub_chunk], code_blocks)[0]
                        
                        chunks.append({
                            'id': chunk_id,
                            'content': sub_chunk.strip(),
                            'length': len(sub_chunk.strip()),
                            'title': section_title,
                            'level': section_level,
                            'part': i + 1 if len(sub_chunks) > 1 else 0,
                            **base_metadata
                        })
                        chunk_id += 1
                elif section_text.strip():
                    if self.preserve_code_blocks:
                        section_text = self._restore_code_blocks([section_text], code_blocks)[0]
                    
                    chunks.append({
                        'id': chunk_id,
                        'content': section_text.strip(),
                        'length': len(section_text.strip()),
                        'title': section_title,
                        'level': section_level,
                        'part': 0,
                        **base_metadata
                    })
                    chunk_id += 1
        else:
            # 普通文本：直接按大小切分
            sub_chunks = self._split_large_section(processed_text)
            for sub_chunk in sub_chunks:
                if self.preserve_code_blocks:
                    sub_chunk = self._restore_code_blocks([sub_chunk], code_blocks)[0]
                
                chunks.append({
                    'id': chunk_id,
                    'content': sub_chunk.strip(),
                    'length': len(sub_chunk.strip()),
                    'title': '',
                    'level': 0,
                    'part': 0,
                    **base_metadata
                })
                chunk_id += 1
        
        # 合并过小的块
        chunks = self._merge_small_chunks(chunks)
        
        # 重新编号
        for i, chunk in enumerate(chunks):
            chunk['id'] = i
        
        return chunks
    
    def _merge_small_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """合并过小的块"""
        if not chunks or self.min_chunk_size <= 0:
            return chunks
        
        merged = []
        buffer = None
        
        for chunk in chunks:
            if buffer is None:
                buffer = chunk.copy()
            elif buffer['length'] < self.min_chunk_size:
                # 当前 buffer 太小，尝试合并
                combined_length = buffer['length'] + chunk['length']
                if combined_length <= self.chunk_size * 1.2:  # 允许略微超出
                    buffer['content'] = buffer['content'] + '\n\n' + chunk['content']
                    buffer['length'] = len(buffer['content'])
                else:
                    merged.append(buffer)
                    buffer = chunk.copy()
            else:
                merged.append(buffer)
                buffer = chunk.copy()
        
        if buffer:
            merged.append(buffer)
        
        return merged


def smart_chunk(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
    min_chunk_size: int = 100,
    metadata: Optional[Dict] = None
) -> List[Dict[str, Any]]:
    """
    便捷函数：对文本进行智能切分
    
    Args:
        text: 待切分的文本
        chunk_size: 目标块大小
        overlap: 重叠字符数
        min_chunk_size: 最小块大小
        metadata: 附加元数据
        
    Returns:
        切分后的块列表
    """
    chunker = SmartChunker(
        chunk_size=chunk_size,
        overlap=overlap,
        min_chunk_size=min_chunk_size
    )
    return chunker.chunk(text, metadata)


if __name__ == "__main__":
    # 测试代码
    test_markdown = """
# 人工智能概述

人工智能（Artificial Intelligence，简称AI）是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。

## 主要应用领域

### 机器人技术

机器人技术是人工智能的重要应用领域之一。现代机器人可以执行复杂的任务，从工业制造到医疗手术。

```python
class Robot:
    def __init__(self, name):
        self.name = name
    
    def move(self, direction):
        print(f"{self.name} moving {direction}")
```

### 自然语言处理

自然语言处理让计算机能够理解人类语言。这包括文本分析、机器翻译、情感分析等多个子领域。自然语言处理的发展使得人机交互变得更加自然和便捷。

## 未来展望

人工智能的发展前景广阔，将会在更多领域发挥重要作用。随着技术的不断进步，AI将更好地服务于人类社会。
"""

    print("=== 智能分块测试 ===\n")
    
    chunks = smart_chunk(test_markdown, chunk_size=300, overlap=50)
    print(f"总块数: {len(chunks)}\n")
    
    for chunk in chunks:
        print(f"Chunk {chunk['id']}:")
        print(f"  标题: {chunk.get('title', '无')}")
        print(f"  长度: {chunk['length']}")
        print(f"  内容预览: {chunk['content'][:80]}...")
        print()
