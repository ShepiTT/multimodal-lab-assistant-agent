"""
父子分块（Parent-Child Chunking）

- 子块（200~400 字符）粒度小、语义集中，负责向量检索的精确命中；
- 父块（800~1500 字符）保留完整上下文，负责喂给大模型生成回答。

每个子块的 dict 中携带 parent_id 与 parent_content，向量库把它们随
metadata 一起持久化；检索命中子块后，用 parent_content 作为生成上下文，
从根上缓解"命中的块太碎、拼不出完整语义"的问题。

切分规则：
- 父块：按段落（空行）边界聚合到目标大小，标题行（Markdown #）强制开新父块；
- 子块：父块内按句子边界聚合，相邻子块保留重叠；
- 代码块（``` 围栏）整体保护，不在中间截断。
"""
import re
from typing import Any, Dict, List

_SENT_END_RE = re.compile(r'(?<=[。！？!?；;\n])')
_CODE_FENCE_RE = re.compile(r'```.*?```', re.DOTALL)


class ParentChildChunker:
    def __init__(self,
                 parent_size: int = 1200,
                 parent_min: int = 800,
                 child_size: int = 300,
                 child_max: int = 400,
                 child_overlap: int = 50):
        self.parent_size = parent_size
        self.parent_min = parent_min
        self.child_size = child_size
        self.child_max = child_max
        self.child_overlap = child_overlap

    # ---- 父块切分 ----

    def _split_blocks(self, text: str) -> List[str]:
        """切成不可再分的原子块：代码块整体保留，其余按段落切。"""
        blocks: List[str] = []
        pos = 0
        for m in _CODE_FENCE_RE.finditer(text):
            before = text[pos:m.start()]
            blocks.extend(p for p in re.split(r'\n\s*\n', before) if p.strip())
            blocks.append(m.group(0))
            pos = m.end()
        blocks.extend(p for p in re.split(r'\n\s*\n', text[pos:]) if p.strip())
        return blocks

    def _build_parents(self, text: str) -> List[str]:
        parents: List[str] = []
        current: List[str] = []
        current_len = 0

        for block in self._split_blocks(text):
            block = block.strip()
            is_heading = bool(re.match(r'^#{1,6}\s', block))
            # 标题开新父块；或者装不下且当前已达最小规模时开新父块
            if current and (
                (is_heading and current_len >= self.parent_min)
                or (current_len + len(block) > self.parent_size and current_len >= self.parent_min)
            ):
                parents.append('\n\n'.join(current))
                current, current_len = [], 0
            current.append(block)
            current_len += len(block)

            # 单块超长（如超大代码块/长段落）：立即独立成父块
            if current_len > self.parent_size * 2:
                parents.append('\n\n'.join(current))
                current, current_len = [], 0

        if current:
            parents.append('\n\n'.join(current))
        return parents

    # ---- 子块切分 ----

    def _split_children(self, parent: str) -> List[str]:
        """父块内切子块；代码围栏（```...```）整体保护为独立子块。"""
        children: List[str] = []
        pos = 0
        for m in _CODE_FENCE_RE.finditer(parent):
            before = parent[pos:m.start()].strip()
            if before:
                children.extend(self._split_text_children(before))
            children.append(m.group(0))
            pos = m.end()
        rest = parent[pos:].strip()
        if rest:
            children.extend(self._split_text_children(rest))
        return children

    def _split_text_children(self, text: str) -> List[str]:
        sentences = [s for s in _SENT_END_RE.split(text) if s.strip()]
        children: List[str] = []
        current = ''
        for sent in sentences:
            # 单句超长：硬切
            while len(sent) > self.child_max:
                if current:
                    children.append(current)
                    current = ''
                children.append(sent[:self.child_max])
                sent = sent[self.child_max:]
            if current and len(current) + len(sent) > self.child_size:
                children.append(current)
                # 重叠：从上一子块尾部带一段
                current = current[-self.child_overlap:] + sent if self.child_overlap else sent
            else:
                current += sent
        if current.strip():
            children.append(current)
        return [c.strip() for c in children if c.strip()]

    # ---- 对外接口（与其它 chunker 一致）----

    def chunk(self, text: str) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []
        chunk_id = 0
        for parent_id, parent in enumerate(self._build_parents(text)):
            title_match = re.match(r'^#{1,6}\s*(.+)', parent)
            title = title_match.group(1).strip()[:50] if title_match else ''
            for child in self._split_children(parent):
                chunks.append({
                    'id': chunk_id,
                    'content': child,
                    'title': title,
                    'length': len(child),
                    'parent_id': parent_id,
                    'parent_content': parent,
                })
                chunk_id += 1
        return chunks
