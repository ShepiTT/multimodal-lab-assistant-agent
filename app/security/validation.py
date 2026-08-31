"""输入校验与上传安全：文件名清洗、kb_type/session_id 白名单、统一上传校验。"""
import re
import uuid
from pathlib import Path

from ..config import DATA_DIR, KB_TYPE_MAP

_SESSION_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,64}$')

# 各类文件的魔数（文件头），用于校验真实类型与扩展名一致
_MAGIC_SIGNATURES = {
    '.pdf': [b'%PDF'],
    '.png': [b'\x89PNG'],
    '.jpg': [b'\xff\xd8\xff'],
    '.jpeg': [b'\xff\xd8\xff'],
    '.bmp': [b'BM'],
    '.docx': [b'PK\x03\x04'],
    '.xlsx': [b'PK\x03\x04'],
    '.mp4': None,   # mp4 头部变体多（ftyp 偏移 4 字节），单独处理
    '.avi': [b'RIFF'],
}

UPLOAD_SIZE_LIMITS = {
    'document': 50 * 1024 * 1024,  # 50MB
    'image': 10 * 1024 * 1024,     # 10MB
    'video': 50 * 1024 * 1024,     # 50MB
}

UPLOAD_ALLOWED_EXTS = {'.docx', '.txt', '.pdf', '.md', '.html', '.csv', '.xlsx',
                       '.jpg', '.jpeg', '.png', '.mp4', '.avi', '.mov', '.flv'}

KB_UPLOAD_ALLOWED_EXTS = {'.docx', '.txt', '.pdf', '.md', '.csv', '.xlsx',
                          '.jpg', '.jpeg', '.png'}


def safe_filename(filename: str) -> str:
    """生成安全的文件名，保留中文字符，只移除路径分隔符和其他危险字符。"""
    if not filename:
        return ""
    safe = filename.replace('/', '_').replace('\\', '_').replace('..', '_')
    safe = safe.replace('<', '_').replace('>', '_').replace(':', '_')
    safe = safe.replace('"', '_').replace('|', '_').replace('?', '_').replace('*', '_')
    return safe.strip()


def resolve_kb_folder(kb_type: str):
    """严格校验 kb_type，返回对应目录名；非法类型返回 None（防止路径拼接越界）。"""
    return KB_TYPE_MAP.get(kb_type)


def validate_session_id(session_id) -> bool:
    """IDE / 会话 id 只允许字母数字、下划线和连字符，防止目录穿越。"""
    return bool(session_id) and bool(_SESSION_ID_RE.match(str(session_id)))


def get_ide_session_dir(session_id) -> Path:
    """校验 session_id 后返回 IDE 会话目录；非法 id 抛 ValueError。"""
    if not validate_session_id(session_id):
        raise ValueError("非法的 session_id")
    return DATA_DIR / "ide_sessions" / session_id


def _sniff_matches(ext: str, header: bytes) -> bool:
    """轻量文件头校验：已知类型必须匹配魔数；未登记的类型不拦截。"""
    if ext == '.mp4':
        return len(header) >= 8 and header[4:8] == b'ftyp'
    sigs = _MAGIC_SIGNATURES.get(ext)
    if sigs is None:
        return True
    return any(header.startswith(sig) for sig in sigs)


def upload_category(ext: str) -> str:
    if ext in {'.jpg', '.jpeg', '.png', '.bmp'}:
        return 'image'
    if ext in {'.mp4', '.avi', '.mov', '.flv'}:
        return 'video'
    return 'document'


def validate_and_save_upload(file, dest_dir: Path, allowed_exts=None):
    """统一的上传校验与保存。

    校验项：扩展名白名单、大小限制、文件头（魔数）、路径越界。
    存储名 = 清洗后的原文件名主干 + 8 位随机后缀，避免覆盖与猜测。
    返回 (safe_name, save_path, size, category)；校验失败抛 ValueError。
    """
    allowed = allowed_exts if allowed_exts is not None else UPLOAD_ALLOWED_EXTS
    original_filename = file.filename or ""
    ext = Path(original_filename).suffix.lower()

    if ext not in allowed:
        raise ValueError(f"不支持的文件类型: {ext or '(无扩展名)'}")

    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)

    category = upload_category(ext)
    limit = UPLOAD_SIZE_LIMITS[category]
    if file_size > limit:
        raise ValueError(f"文件大小超过限制 ({limit / (1024 * 1024):.0f}MB)")
    if file_size == 0:
        raise ValueError("文件内容为空")

    header = file.read(16)
    file.seek(0)
    if not _sniff_matches(ext, header):
        raise ValueError(f"文件内容与扩展名 {ext} 不匹配")

    stem = safe_filename(Path(original_filename).stem) or "file"
    safe_name = f"{stem}_{uuid.uuid4().hex[:8]}{ext}"

    dest_dir.mkdir(parents=True, exist_ok=True)
    save_path = (dest_dir / safe_name).resolve()
    if dest_dir.resolve() not in save_path.parents:
        raise ValueError("非法的存储路径")

    file.save(save_path)
    return safe_name, save_path, file_size, category
