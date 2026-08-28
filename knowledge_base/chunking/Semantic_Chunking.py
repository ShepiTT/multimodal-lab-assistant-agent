"""
语义分块 (Semantic Chunking)
基于文档结构（标题、段落）进行语义切分，保持内容的逻辑完整性
"""
import re
from typing import List, Dict, Any, Optional


class SemanticChunker:
    """基于语义的文本切分器"""
    
    def __init__(self, max_chunk_size: int = 1000, min_chunk_size: int = 100):
        """
        初始化切分器
        
        Args:
            max_chunk_size: 每个块的最大字符数
            min_chunk_size: 每个块的最小字符数
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        
        # Markdown标题正则表达式
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        # 段落分隔符
        self.paragraph_pattern = re.compile(r'\n\s*\n')
    
    def _extract_sections(self, text: str) -> List[Dict[str, Any]]:
        """提取文档的章节结构"""
        sections = []
        lines = text.split('\n')
        current_section = {
            'level': 0,
            'title': 'Root',
            'content': [],
            'subsections': []
        }
        section_stack = [current_section]
        
        for line in lines:
            heading_match = self.heading_pattern.match(line)
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                new_section = {
                    'level': level,
                    'title': title,
                    'content': [],
                    'subsections': []
                }
                
                # 找到合适的父节点
                while len(section_stack) > 1 and section_stack[-1]['level'] >= level:
                    section_stack.pop()
                
                section_stack[-1]['subsections'].append(new_section)
                section_stack.append(new_section)
            else:
                if line.strip():
                    section_stack[-1]['content'].append(line)
        
        return current_section['subsections'] if current_section['subsections'] else [current_section]
    
    def _flatten_sections(self, sections: List[Dict], parent_title: str = "") -> List[Dict[str, Any]]:
        """将嵌套的章节结构展平"""
        result = []
        
        for section in sections:
            full_title = f"{parent_title} > {section['title']}" if parent_title else section['title']
            content = '\n'.join(section['content'])
            
            if content.strip():
                result.append({
                    'title': full_title,
                    'content': content,
                    'level': section['level']
                })
            
            # 递归处理子章节
            if section['subsections']:
                result.extend(self._flatten_sections(section['subsections'], full_title))
        
        return result
    
    def chunk(self, text: str) -> List[Dict[str, Any]]:
        """
        对文本进行语义切分
        
        Args:
            text: 待切分的文本（支持Markdown格式）
            
        Returns:
            切分后的文本块列表
        """
        if not text or not text.strip():
            return []
        
        # 提取章节结构
        sections = self._extract_sections(text)
        flat_sections = self._flatten_sections(sections)
        
        chunks = []
        chunk_id = 0
        
        for section in flat_sections:
            content = section['content']
            title = section['title']
            
            # 如果内容超过最大长度，需要进一步切分
            if len(content) > self.max_chunk_size:
                # 按段落切分
                paragraphs = self.paragraph_pattern.split(content)
                current_chunk = []
                current_length = 0
                
                for para in paragraphs:
                    para = para.strip()
                    if not para:
                        continue
                    
                    para_length = len(para)
                    
                    if current_length + para_length > self.max_chunk_size and current_chunk:
                        chunks.append({
                            'id': chunk_id,
                            'title': title,
                            'content': '\n\n'.join(current_chunk),
                            'length': current_length,
                            'level': section['level']
                        })
                        chunk_id += 1
                        current_chunk = []
                        current_length = 0
                    
                    current_chunk.append(para)
                    current_length += para_length
                
                if current_chunk:
                    chunks.append({
                        'id': chunk_id,
                        'title': title,
                        'content': '\n\n'.join(current_chunk),
                        'length': current_length,
                        'level': section['level']
                    })
                    chunk_id += 1
            else:
                chunks.append({
                    'id': chunk_id,
                    'title': title,
                    'content': content,
                    'length': len(content),
                    'level': section['level']
                })
                chunk_id += 1
        
        return chunks


def semantic_chunk(text: str, max_chunk_size: int = 1000, min_chunk_size: int = 100) -> List[Dict[str, Any]]:
    """
    便捷函数：对文本进行语义切分
    
    Args:
        text: 待切分的文本
        max_chunk_size: 每个块的最大字符数
        min_chunk_size: 每个块的最小字符数
        
    Returns:
        切分后的文本块列表
    """
    chunker = SemanticChunker(max_chunk_size=max_chunk_size, min_chunk_size=min_chunk_size)
    return chunker.chunk(text)


if __name__ == "__main__":
    # 测试代码
    test_text = """
# 人工智能概述

## 定义
人工智能是计算机科学的一个分支，它企图了解智能的实质。

## 应用领域

### 机器人
机器人技术是人工智能的重要应用领域之一。

### 自然语言处理
自然语言处理让计算机能够理解人类语言。
"""
    
    chunks = semantic_chunk(test_text, max_chunk_size=200)
    for chunk in chunks:
        print(f"Chunk {chunk['id']} [{chunk['title']}]: {chunk['content'][:50]}...")
