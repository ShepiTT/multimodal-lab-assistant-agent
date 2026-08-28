"""
混合分块 (Hybrid Chunking)
结合文档结构分块和递归字符分块的优点：
1. 首先基于 Markdown 标题进行高级别分割
2. 对超出大小限制的块使用递归分隔符进行细粒度切分
3. 保护代码块完整性，不对代码块内容进行切分
"""
import yaml
import re
import copy
from typing import Dict, List, Optional, Tuple, TypedDict, Callable
from dataclasses import dataclass, field


@dataclass
class Chunk:
    """用于存储文本片段及相关元数据的类。"""
    content: str = ''
    metadata: dict = field(default_factory=dict)

    def __str__(self) -> str:
        if self.metadata:
            return f"content='{self.content}' metadata={self.metadata}"
        else:
            return f"content='{self.content}'"

    def __repr__(self) -> str:
        return self.__str__()

    def to_markdown(self, return_all: bool = False) -> str:
        """将块转换为 Markdown 格式。
        
        Args:
            return_all: 如果为 True，则在内容前包含 YAML 格式的元数据。
        
        Returns:
            Markdown 格式的字符串。
        """
        md_string = ""
        if return_all and self.metadata:
            metadata_yaml = yaml.dump(self.metadata, allow_unicode=True, sort_keys=False)
            md_string += f"---\n{metadata_yaml}---\n\n"
        md_string += self.content
        return md_string
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'content': self.content,
            'metadata': self.metadata,
            'length': len(self.content)
        }


class LineType(TypedDict):
    """行类型"""
    metadata: Dict[str, str]
    content: str


class HeaderType(TypedDict):
    """标题类型"""
    level: int
    name: str
    data: str


class HybridChunker:
    """混合文本切分器：基于 Markdown 结构 + 递归字符分割"""

    def __init__(
        self,
        headers_to_split_on: List[Tuple[str, str]] = None,
        strip_headers: bool = False,
        chunk_size: Optional[int] = 500,
        length_function: Callable[[str], int] = len,
        separators: Optional[List[str]] = None,
        is_separator_regex: bool = False,
    ):
        """
        初始化混合切分器
        
        Args:
            headers_to_split_on: 用于分割的标题级别和名称元组列表
            strip_headers: 是否从块内容中移除标题行
            chunk_size: 块的最大非代码内容长度
            length_function: 用于计算文本长度的函数
            separators: 用于分割的分隔符列表，优先级从高到低
            is_separator_regex: 是否将分隔符视为正则表达式
        """
        if chunk_size is not None and chunk_size <= 0:
            raise ValueError("chunk_size 必须是正整数或 None。")

        self.headers_to_split_on = headers_to_split_on or [
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
            ("####", "h4"),
            ("#####", "h5"),
            ("######", "h6"),
        ]
        self.headers_to_split_on = sorted(
            self.headers_to_split_on, key=lambda split: len(split[0]), reverse=True
        )
        self.strip_headers = strip_headers
        self._chunk_size = chunk_size
        self._length_function = length_function
        # 默认分隔符优先级
        self._separators = separators or [
            "\n\n",           # 段落
            "\n",             # 行
            "。|！|？",        # 中文句末标点
            r"\.\s|\!\s|\?\s", # 英文句末标点加空格
            "；|;\s",          # 分号
            "，|,\s"           # 逗号
        ]
        self._is_separator_regex = is_separator_regex
        self._compiled_separators = None
        if self._is_separator_regex:
            self._compiled_separators = [re.compile(s) for s in self._separators]

    def _calculate_length_excluding_code(self, text: str) -> int:
        """计算文本长度，不包括代码块内容。"""
        total_length = 0
        last_end = 0
        for match in re.finditer(r"(?:```|~~~).*?\n(?:.*?)(?:```|~~~)", text, re.DOTALL | re.MULTILINE):
            start, end = match.span()
            total_length += self._length_function(text[last_end:start])
            last_end = end
        total_length += self._length_function(text[last_end:])
        return total_length

    def _find_best_split_point(self, lines: List[str]) -> int:
        """在行列表中查找最佳分割点。"""
        if len(lines) <= 1:
            return -1

        # 优先查找段落分隔符 "\n\n"
        for i in range(len(lines) - 2, 0, -1):
            if not lines[i].strip() and lines[i+1].strip():
                if i > 0 and lines[i-1].strip():
                    return i + 1

        if len(lines) > 1:
            return len(lines) - 1

        return -1

    def _split_chunk_by_size(self, chunk: Chunk) -> List[Chunk]:
        """将超出 chunk_size 的块分割成更小的块。"""
        if self._chunk_size is None:
            return [chunk]

        sub_chunks = []
        current_lines = []
        current_non_code_len = 0
        in_code = False
        code_fence = None
        lines = chunk.content.split('\n')

        for line_idx, line in enumerate(lines):
            stripped_line = line.strip()
            is_entering_code = False
            is_exiting_code = False

            # 代码块边界检查
            if not in_code:
                if stripped_line.startswith("```") and stripped_line.count("```") == 1:
                    is_entering_code = True
                    code_fence = "```"
                elif stripped_line.startswith("~~~") and stripped_line.count("~~~") == 1:
                    is_entering_code = True
                    code_fence = "~~~"
            elif in_code and code_fence is not None and stripped_line.startswith(code_fence):
                is_exiting_code = True

            # 计算行长度贡献
            line_len_contribution = 0
            if not in_code and not is_entering_code:
                line_len_contribution = self._length_function(line) + 1
            elif is_exiting_code:
                line_len_contribution = self._length_function(line) + 1

            # 检查是否需要分割
            split_needed = (
                line_len_contribution > 0 and
                current_non_code_len + line_len_contribution > self._chunk_size and
                current_lines
            )

            if split_needed:
                split_line_idx = self._find_best_split_point(current_lines)

                if split_line_idx != -1 and split_line_idx > 0:
                    lines_to_chunk = current_lines[:split_line_idx]
                    remaining_lines = current_lines[split_line_idx:]

                    content = "\n".join(lines_to_chunk)
                    sub_chunks.append(Chunk(content=content, metadata=chunk.metadata.copy()))

                    current_lines = remaining_lines + [line]
                    current_non_code_len = self._calculate_length_excluding_code("\n".join(current_lines))
                else:
                    content = "\n".join(current_lines)
                    sub_chunks.append(Chunk(content=content, metadata=chunk.metadata.copy()))
                    current_lines = [line]
                    current_non_code_len = line_len_contribution if not is_entering_code else 0
            else:
                current_lines.append(line)
                if line_len_contribution > 0:
                    current_non_code_len += line_len_contribution

            # 更新代码块状态
            if is_entering_code:
                in_code = True
            elif is_exiting_code:
                in_code = False
                code_fence = None

        # 添加最后一个子块
        if current_lines:
            content = "\n".join(current_lines)
            sub_chunks.append(Chunk(content=content, metadata=chunk.metadata.copy()))

        return sub_chunks if sub_chunks else [chunk]

    def _aggregate_lines_to_chunks(self, lines: List[LineType], base_meta: dict) -> List[Chunk]:
        """将具有共同元数据的行合并成块。"""
        aggregated_chunks: List[LineType] = []

        for line in lines:
            if aggregated_chunks and aggregated_chunks[-1]["metadata"] == line["metadata"]:
                aggregated_chunks[-1]["content"] += "\n" + line["content"]
            else:
                aggregated_chunks.append(copy.deepcopy(line))

        final_chunks = []
        for chunk_data in aggregated_chunks:
            final_metadata = base_meta.copy()
            final_metadata.update(chunk_data['metadata'])
            final_chunks.append(
                Chunk(content=chunk_data["content"], metadata=final_metadata)
            )
        return final_chunks

    def chunk(self, text: str, metadata: Optional[dict] = None) -> List[Chunk]:
        """
        对文本进行混合切分
        
        Args:
            text: 待切分的 Markdown 文本
            metadata: 附加的基础元数据
            
        Returns:
            切分后的 Chunk 列表
        """
        if not text or not text.strip():
            return []
            
        base_metadata = metadata or {}
        lines = text.split("\n")
        lines_with_metadata: List[LineType] = []
        current_content: List[str] = []
        current_metadata: Dict[str, str] = {}
        header_stack: List[HeaderType] = []

        in_code_block = False
        opening_fence = ""

        for line_num, line in enumerate(lines):
            stripped_line = line.strip()

            # 代码块处理
            is_code_fence = False
            if not in_code_block:
                if stripped_line.startswith("```") and stripped_line.count("```") == 1:
                    in_code_block = True
                    opening_fence = "```"
                    is_code_fence = True
                elif stripped_line.startswith("~~~") and stripped_line.count("~~~") == 1:
                    in_code_block = True
                    opening_fence = "~~~"
                    is_code_fence = True
            elif in_code_block and opening_fence and stripped_line.startswith(opening_fence):
                in_code_block = False
                opening_fence = ""
                is_code_fence = True

            if in_code_block or is_code_fence:
                current_content.append(line)
                continue

            # 标题处理
            found_header = False
            for sep, name in self.headers_to_split_on:
                if stripped_line.startswith(sep) and (
                    len(stripped_line) == len(sep) or stripped_line[len(sep)] == " "
                ):
                    found_header = True
                    header_level = sep.count("#")
                    header_data = stripped_line[len(sep):].strip()

                    if current_content:
                        lines_with_metadata.append({
                            "content": "\n".join(current_content),
                            "metadata": current_metadata.copy(),
                        })
                        current_content = []

                    while header_stack and header_stack[-1]["level"] >= header_level:
                        header_stack.pop()
                    new_header: HeaderType = {"level": header_level, "name": name, "data": header_data}
                    header_stack.append(new_header)
                    current_metadata = {h["name"]: h["data"] for h in header_stack}

                    if not self.strip_headers:
                        current_content.append(line)
                    break

            if not found_header:
                if line.strip() or current_content:
                    current_content.append(line)

        # 处理剩余内容
        if current_content:
            lines_with_metadata.append({
                "content": "\n".join(current_content),
                "metadata": current_metadata.copy(),
            })

        # 第一步：基于标题聚合块
        aggregated_chunks = self._aggregate_lines_to_chunks(lines_with_metadata, base_meta=base_metadata)

        # 第二步：如果设置了 chunk_size，则进一步细分块
        if self._chunk_size is None:
            return aggregated_chunks
        else:
            final_chunks = []
            for chunk in aggregated_chunks:
                non_code_len = self._calculate_length_excluding_code(chunk.content)
                if non_code_len > self._chunk_size:
                    split_sub_chunks = self._split_chunk_by_size(chunk)
                    final_chunks.extend(split_sub_chunks)
                else:
                    final_chunks.append(chunk)
            return final_chunks
    
    def chunk_to_dicts(self, text: str, metadata: Optional[dict] = None) -> List[Dict]:
        """
        对文本进行混合切分，返回字典列表格式
        
        Args:
            text: 待切分的 Markdown 文本
            metadata: 附加的基础元数据
            
        Returns:
            切分后的字典列表，每个字典包含 id, content, metadata, length
        """
        chunks = self.chunk(text, metadata)
        return [
            {
                'id': i,
                'content': chunk.content,
                'metadata': chunk.metadata,
                'length': len(chunk.content)
            }
            for i, chunk in enumerate(chunks)
        ]



def hybrid_chunk(
    text: str, 
    chunk_size: int = 500, 
    metadata: Optional[dict] = None,
    strip_headers: bool = False
) -> List[Dict]:
    """
    便捷函数：对文本进行混合切分
    
    Args:
        text: 待切分的 Markdown 文本
        chunk_size: 块的最大非代码内容长度
        metadata: 附加的基础元数据
        strip_headers: 是否从块内容中移除标题行
        
    Returns:
        切分后的字典列表
    """
    chunker = HybridChunker(chunk_size=chunk_size, strip_headers=strip_headers)
    return chunker.chunk_to_dicts(text, metadata)


if __name__ == "__main__":
    # 测试代码
    test_text = """
# 人工智能概述

人工智能（Artificial Intelligence，简称AI）是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。

## 主要应用领域

### 机器人技术

机器人技术是人工智能的重要应用领域之一。现代机器人可以执行复杂的任务，从工业制造到医疗手术。

```python
# 示例代码：简单的机器人控制
class Robot:
    def __init__(self, name):
        self.name = name
    
    def move(self, direction):
        print(f"{self.name} moving {direction}")
```

### 自然语言处理

自然语言处理让计算机能够理解人类语言。这包括文本分析、机器翻译、情感分析等多个子领域。

## 未来展望

人工智能的发展前景广阔，将会在更多领域发挥重要作用。
"""

    print("=== 混合分块测试 ===\n")
    
    # 策略1：仅基于标题分割
    print("--- 策略1: 仅基于标题分割 (无 chunk_size 限制) ---")
    chunker_no_limit = HybridChunker(chunk_size=None)
    chunks_no_limit = chunker_no_limit.chunk(test_text)
    print(f"总块数: {len(chunks_no_limit)}")
    for i, chunk in enumerate(chunks_no_limit):
        print(f"\nChunk {i+1}:")
        print(f"  元数据: {chunk.metadata}")
        print(f"  长度: {len(chunk.content)}")
        print(f"  内容预览: {chunk.content[:60]}...")
    
    print("\n" + "=" * 60 + "\n")
    
    # 策略2：基于标题 + chunk_size 限制
    print("--- 策略2: 基于标题 + chunk_size=150 限制 ---")
    chunker_with_limit = HybridChunker(chunk_size=150, is_separator_regex=True)
    chunks_with_limit = chunker_with_limit.chunk(test_text)
    print(f"总块数: {len(chunks_with_limit)}")
    for i, chunk in enumerate(chunks_with_limit):
        non_code_len = chunker_with_limit._calculate_length_excluding_code(chunk.content)
        print(f"\nChunk {i+1}:")
        print(f"  元数据: {chunk.metadata}")
        print(f"  总长度: {len(chunk.content)}, 非代码长度: {non_code_len}")
        print(f"  内容预览: {chunk.content[:60]}...")
    
    print("\n" + "=" * 60 + "\n")
    
    # 使用便捷函数
    print("--- 使用便捷函数 hybrid_chunk ---")
    result = hybrid_chunk(test_text, chunk_size=200)
    print(f"总块数: {len(result)}")
    for chunk in result:
        print(f"Chunk {chunk['id']}: {chunk['content'][:50]}... (长度: {chunk['length']})")
