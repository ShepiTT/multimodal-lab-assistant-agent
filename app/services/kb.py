"""知识库实例缓存与 text.json 元数据管理。"""
import json
from typing import Any, Dict

from ..config import KB_BASE_DIR, timestamp
from ..security.validation import resolve_kb_folder
from .. import runtime

# 知识库实例缓存
_kb_instances: Dict[str, Any] = {}


def get_kb_instance(kb_type: str):
    """获取或创建知识库实例"""
    if not runtime.KB_AVAILABLE:
        return None

    kb_folder = resolve_kb_folder(kb_type)
    if kb_folder is None:
        return None
    kb_dir = KB_BASE_DIR / kb_folder
    index_file = kb_dir / "index" / "index.pkl"

    # 如果索引文件不存在，清除缓存的实例并返回 None
    if not index_file.exists():
        if kb_type in _kb_instances:
            print(f"[KB] 索引文件不存在，清除缓存的实例: {kb_type}")
            del _kb_instances[kb_type]
        print(f"[KB] 索引文件不存在，无法加载知识库: {index_file}")
        return None

    if kb_type not in _kb_instances:
        try:
            kb = runtime.FaultDiagnosisKnowledgeBase(
                data_dir=str(kb_dir),
                chunk_method="smart",  # 使用智能切分
                chunk_size=500,
                device=None  # 自动检测 GPU
            )
            print(f"[KB] 正在加载已有索引: {index_file}")
            kb.load_index()
            print(f"[KB] 索引加载成功，文档数: {kb.vector_store.index.ntotal if kb.vector_store else 0}")
            _kb_instances[kb_type] = kb
        except Exception as e:
            print(f"[KB] 加载知识库失败 ({kb_type}): {e}")
            import traceback
            traceback.print_exc()
            return None

    return _kb_instances.get(kb_type)


def load_kb_json(kb_type: str) -> Dict:
    """加载知识库的 text.json 配置文件"""
    kb_folder = resolve_kb_folder(kb_type)
    if kb_folder is None:
        return {"files": [], "last_updated": None, "index_built": False, "total_chunks": 0}
    json_path = KB_BASE_DIR / kb_folder / "data" / "text.json"

    if json_path.exists():
        try:
            with json_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    return {"files": [], "last_updated": None, "index_built": False, "total_chunks": 0}


def save_kb_json(kb_type: str, data: Dict):
    """保存知识库的 text.json 配置文件"""
    kb_folder = resolve_kb_folder(kb_type)
    if kb_folder is None:
        raise ValueError(f"无效的知识库类型: {kb_type}")
    kb_data_dir = KB_BASE_DIR / kb_folder / "data"
    kb_data_dir.mkdir(parents=True, exist_ok=True)
    json_path = kb_data_dir / "text.json"

    data["last_updated"] = timestamp()
    with json_path.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
