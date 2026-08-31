"""会话历史（JSONL 文件，每个会话一个文件）。"""
import json
import uuid
from pathlib import Path
from typing import Optional

from ..config import HISTORY_DIR, ensure_dirs, timestamp


def get_session_file(session_id: str) -> Path:
    """获取会话对应的历史文件路径"""
    ensure_dirs()
    return HISTORY_DIR / f"{session_id}.jsonl"


def append_history(role: str, content: str, meta: Optional[dict] = None, session_id: Optional[str] = None):
    """追加一条历史记录到会话文件。"""
    if not session_id:
        session_id = str(uuid.uuid4())

    session_file = get_session_file(session_id)
    record = {
        "role": role,
        "content": content,
        "timestamp": timestamp(),
        "meta": meta or {}
    }
    with session_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_history(limit: int = 50, session_id: Optional[str] = None):
    """读取历史记录。
       如果指定 session_id，则返回该会话的所有记录（按时间正序）。
       如果未指定 session_id，则返回会话列表（每个会话的摘要信息，按时间倒序）。
    """
    ensure_dirs()

    if session_id:
        session_file = get_session_file(session_id)
        if not session_file.exists():
            return []
        records = []
        with session_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records

    sessions = []
    for file in HISTORY_DIR.glob("*.jsonl"):
        sid = file.stem
        first_user_msg = ""
        last_timestamp = ""
        with file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    last_timestamp = rec.get("timestamp", "")
                    if not first_user_msg and rec.get("role") == "user":
                        first_user_msg = rec.get("content", "")[:50]
                except json.JSONDecodeError:
                    continue

        sessions.append({
            "session_id": sid,
            "title": first_user_msg or "新对话",
            "timestamp": last_timestamp,
            "updated_at": file.stat().st_mtime
        })

    sessions.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
    return sessions[:limit]
