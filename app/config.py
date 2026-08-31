"""全局配置：路径常量、环境变量、模型与提示词配置文件读写。"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# 项目根目录（app/ 包的上一级）
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
VOICE_DATA_DIR = DATA_DIR / "voice"  # 录音文件放在 data/voice 目录
HISTORY_DIR = DATA_DIR / "history"  # 每个会话一个文件
FAVICON_FILE = BASE_DIR / "favicon.ico"
KB_BASE_DIR = BASE_DIR / "knowledge_base"
LOG_DIR = BASE_DIR / "log"

# 知识库类型映射（白名单：未知类型一律拒绝，防止路径拼接越界）
KB_TYPE_MAP = {
    'guide': 'operating_instructions',
    'diagnosis': 'fault_diagnosis',
    'safety': 'safety_regulations',
    'debug': 'code_debug'
}

DEFAULT_BASE_URLS = {
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "volcengine": "https://ark.cn-beijing.volces.com/api/v3",
    "deepseek": "https://api.deepseek.com",
    "local": os.environ.get("LOCAL_LLM_BASE_URL", ""),  # 允许通过环境变量覆盖
    "openai": None,  # 官方默认
}

LLM_CONFIG_FILE = BASE_DIR / "models" / "models_config.json"
SYSTEM_PROMPT_FILE = BASE_DIR / "config" / "system_prompt.json"


def env_flag(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).lower() in ("true", "1", "yes")


def ensure_dirs():
    for directory in (DATA_DIR, UPLOAD_DIR, VOICE_DATA_DIR, HISTORY_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def timestamp():
    return datetime.utcnow().isoformat() + "Z"


def resolve_api_key(raw_api_key: str, provider_id: str) -> str:
    """根据 provider 尝试从环境变量回落获取 API Key。"""
    if raw_api_key:
        return raw_api_key

    provider_envs = {
        "qwen": ["ALI_API_KEY", "DASHSCOPE_API_KEY", "OPENAI_API_KEY", "API_KEY"],
        "volcengine": ["ARK_API_KEY", "OPENAI_API_KEY", "API_KEY"],
        "deepseek": ["DEEPSEEK_API_KEY", "OPENAI_API_KEY", "API_KEY"],
        "local": ["LOCAL_API_KEY", "OPENAI_API_KEY", "API_KEY"],
        "openai": ["OPENAI_API_KEY", "API_KEY"],
    }
    env_order = provider_envs.get(provider_id, ["OPENAI_API_KEY"])
    for k in env_order:
        val = os.environ.get(k)
        if val:
            return val
    return ""


def load_llm_config() -> Dict[str, Any]:
    """读取 models_config.json，供前端模型选择使用。"""
    if not LLM_CONFIG_FILE.exists():
        return {"providers": [], "defaults": {}}
    with LLM_CONFIG_FILE.open("r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"providers": [], "defaults": {}}


def load_system_prompt_config() -> Dict[str, Any]:
    """读取系统提示词配置"""
    if not SYSTEM_PROMPT_FILE.exists():
        return {"default": "", "presets": {}}
    with SYSTEM_PROMPT_FILE.open("r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"default": "", "presets": {}}


def save_system_prompt_config(config: Dict[str, Any]):
    """保存系统提示词配置"""
    SYSTEM_PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SYSTEM_PROMPT_FILE.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_system_prompt() -> str:
    """获取当前系统提示词"""
    config = load_system_prompt_config()
    return config.get("default", "")
