from flask import Flask, render_template, request, jsonify, send_from_directory, Response, stream_with_context
from flask_compress import Compress
from werkzeug.utils import secure_filename
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from openai import OpenAI
import sys
import subprocess
import time
import platform

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.append(str(APP_ROOT))


# ==================== Docker 和 Piston 自动启动 ====================
def check_docker_installed():
    """检查 Docker 是否安装"""
    try:
        result = subprocess.run(['docker', '--version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_docker_running():
    """检查 Docker 是否运行"""
    try:
        result = subprocess.run(['docker', 'info'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def start_docker_desktop():
    """启动 Docker Desktop"""
    system = platform.system()
    try:
        if system == 'Windows':
            docker_path = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
            if Path(docker_path).exists():
                subprocess.Popen([docker_path], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
                print("⏳ 正在启动 Docker Desktop，请稍候...")
                # 等待 Docker 启动
                for i in range(30):
                    time.sleep(1)
                    if check_docker_running():
                        print("✅ Docker Desktop 已启动")
                        return True
                print("⚠️  Docker Desktop 启动超时，请手动检查")
                return False
        elif system == 'Darwin':  # macOS
            subprocess.Popen(['open', '-a', 'Docker'], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            print("⏳ 正在启动 Docker Desktop，请稍候...")
            for i in range(30):
                time.sleep(1)
                if check_docker_running():
                    print("✅ Docker Desktop 已启动")
                    return True
            return False
        else:  # Linux
            print("⚠️  请手动启动 Docker 服务: sudo systemctl start docker")
            return False
    except Exception as e:
        print(f"❌ 启动 Docker Desktop 失败: {e}")
        return False


def check_piston_running():
    """检查 Piston 容器是否运行"""
    try:
        result = subprocess.run(['docker', 'ps', '--filter', 'name=piston', '--format', '{{.Names}}'],
                              capture_output=True,
                              text=True,
                              timeout=5)
        return 'piston' in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def start_piston_container():
    """启动 Piston 容器"""
    try:
        print("📦 正在启动 Piston 容器...")
        result = subprocess.run(['docker', 'compose', '-p', 'piston', 'up', '-d'],
                              capture_output=True,
                              text=True,
                              timeout=60,
                              cwd=str(APP_ROOT))
        
        if result.returncode == 0:
            print("✅ Piston 容器已启动")
            # 等待容器完全启动
            time.sleep(3)
            return True
        else:
            print(f"⚠️  Piston 启动失败: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("⚠️  Piston 启动超时")
        return False
    except Exception as e:
        print(f"❌ 启动 Piston 失败: {e}")
        return False


def test_piston_connection():
    """测试 Piston 连接"""
    try:
        import requests
        response = requests.get('http://localhost:2000/api/v2/runtimes', timeout=5)
        if response.status_code == 200:
            runtimes = response.json()
            if len(runtimes) == 0:
                print(f"⚠️  Piston 连接正常，但没有安装语言包")
                print(f"   运行以下命令安装常用语言:")
                print(f"   python install_languages.py")
                return False
            else:
                print(f"✅ Piston 连接正常，支持 {len(runtimes)} 种语言")
                # 显示已安装的语言
                langs = set(r['language'] for r in runtimes)
                print(f"   已安装: {', '.join(sorted(langs))}")
                return True
        else:
            print(f"⚠️  Piston 响应异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️  Piston 连接测试失败: {e}")
        return False


def initialize_docker_and_piston():
    """初始化 Docker 和 Piston"""
    print("\n" + "="*60)
    print("🚀 初始化代码执行引擎")
    print("="*60)
    
    # 检查 Docker 是否安装
    if not check_docker_installed():
        print("❌ Docker 未安装")
        print("   请访问 https://www.docker.com/products/docker-desktop 下载安装")
        print("   应用将继续启动，但代码执行功能不可用")
        return False
    
    print("✅ Docker 已安装")
    
    # 检查 Docker 是否运行
    if not check_docker_running():
        print("📦 Docker 未运行，正在启动...")
        if not start_docker_desktop():
            print("❌ Docker 启动失败")
            print("   请手动启动 Docker Desktop")
            print("   应用将继续启动，但代码执行功能不可用")
            return False
    else:
        print("✅ Docker 正在运行")
    
    # 检查 Piston 容器是否运行
    if not check_piston_running():
        print("📦 Piston 容器未运行，正在启动...")
        if not start_piston_container():
            print("❌ Piston 启动失败")
            print("   应用将继续启动，但代码执行功能不可用")
            return False
    else:
        print("✅ Piston 容器正在运行")
    
    # 测试 Piston 连接
    test_piston_connection()
    
    print("="*60)
    print()
    return True

# ==================== 结束 Docker 和 Piston 自动启动 ====================
try:
    from models.LLM.llm_runner import call_model, call_model_stream  # 统一模型调用
except Exception as e:
    call_model = None
    call_model_stream = None
    print(f"[warn] 未能导入 models.LLM.llm_runner: {e}")
from dotenv import load_dotenv
import uuid
import json
import os
import base64
import requests
try:
    from config import get_asr_model_config
except Exception as e:
    get_asr_model_config = None
    print(f"[warn] 未能导入 config.get_asr_model_config: {e}")

try:
    from parsing_service.parser import parse_file, parse_for_chat, validate_file, ALL_EXTENSIONS, SIZE_LIMITS
except Exception as e:
    parse_file = None
    parse_for_chat = None
    print(f"[warn] 未能导入 parsing_service: {e}")

# 导入知识库模块
try:
    from knowledge_base.fault_diagnosis.vector_store import FaultDiagnosisKnowledgeBase
    KB_AVAILABLE = True
except Exception as e:
    FaultDiagnosisKnowledgeBase = None
    KB_AVAILABLE = False
    print(f"[warn] 未能导入知识库模块: {e}")

# 导入 Prompt 引擎模块
try:
    from prompt_engine import get_prompt_engine, ScenarioType
    from prompt_engine.api_integration import (
        register_prompt_engine_routes,
        integrate_with_chat_stream,
        detect_scenario_from_message
    )
    PROMPT_ENGINE_AVAILABLE = True
except Exception as e:
    get_prompt_engine = None
    ScenarioType = None
    register_prompt_engine_routes = None
    integrate_with_chat_stream = None
    detect_scenario_from_message = None
    PROMPT_ENGINE_AVAILABLE = False
    print(f"[warn] 未能导入 Prompt 引擎模块: {e}")

# 导入统一的 ASR/OCR/TTS runner
try:
    from models.ASR.asr_runner import recognize as asr_recognize
except Exception as e:
    asr_recognize = None
    print(f"[warn] 未能导入 models.ASR.asr_runner: {e}")

try:
    from models.OCR.ocr_runner import recognize as ocr_recognize, recognize_bytes as ocr_recognize_bytes
except Exception as e:
    ocr_recognize = None
    ocr_recognize_bytes = None
    print(f"[warn] 未能导入 models.OCR.ocr_runner: {e}")

try:
    from models.ASR.convert import convert_to_wav, check_ffmpeg
except Exception as e:
    convert_to_wav = None
    check_ffmpeg = None
    print(f"[warn] 未能导入 models.ASR.convert: {e}")

try:
    from models.TTS.tts_runner import synthesize as tts_synthesize
except Exception as e:
    tts_synthesize = None
    print(f"[warn] 未能导入 models.TTS.tts_runner: {e}")

# 导入联网搜索模块
try:
    from web_search.search_api import search_and_format, search_web, format_search_results
    WEB_SEARCH_AVAILABLE = True
except Exception as e:
    search_and_format = None
    search_web = None
    format_search_results = None
    WEB_SEARCH_AVAILABLE = False
    print(f"[warn] 未能导入 web_search.search_api: {e}")

# 设置模板文件夹和静态文件夹为当前目录，这样可以直接使用 index.html
app = Flask(__name__, template_folder='.', static_folder='.')

# 启用 Gzip 压缩 - 可以将响应体积减少 60-70%
Compress(app)

# 注册 Prompt 引擎路由
if PROMPT_ENGINE_AVAILABLE and register_prompt_engine_routes:
    try:
        register_prompt_engine_routes(app)
        print("[info] Prompt 引擎路由已注册")
    except Exception as e:
        print(f"[warn] 注册 Prompt 引擎路由失败: {e}")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
VOICE_DATA_DIR = DATA_DIR / "voice"  # 录音文件放在 data/voice 目录
HISTORY_DIR = DATA_DIR / "history"  # 每个会话一个文件
FAVICON_FILE = BASE_DIR / "favicon.ico"
KB_BASE_DIR = BASE_DIR / "knowledge_base"

# 知识库类型映射
KB_TYPE_MAP = {
    'guide': 'operating_instructions',
    'diagnosis': 'fault_diagnosis',
    'safety': 'safety_regulations',
    'debug': 'code_debug'
}

# 知识库实例缓存
_kb_instances: Dict[str, Any] = {}

DEFAULT_BASE_URLS = {
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "volcengine": "https://ark.cn-beijing.volces.com/api/v3",
    "deepseek": "https://api.deepseek.com",
    "local": os.environ.get("LOCAL_LLM_BASE_URL", ""),  # 允许通过环境变量覆盖
    "openai": None,  # 官方默认
}
LLM_CONFIG_FILE = BASE_DIR / "models" / "models_config.json"

# 预先加载项目根目录下的 .env（便于读取本地存放的 API Key）
load_dotenv(BASE_DIR / ".env")


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


def ensure_dirs():
    for directory in (DATA_DIR, UPLOAD_DIR, VOICE_DATA_DIR, HISTORY_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def safe_filename(filename: str) -> str:
    """
    生成安全的文件名，保留中文字符
    只移除路径分隔符和其他危险字符
    """
    if not filename:
        return ""
    # 移除路径分隔符和危险字符
    safe = filename.replace('/', '_').replace('\\', '_').replace('..', '_')
    safe = safe.replace('<', '_').replace('>', '_').replace(':', '_')
    safe = safe.replace('"', '_').replace('|', '_').replace('?', '_').replace('*', '_')
    return safe.strip()


def get_session_file(session_id: str) -> Path:
    """获取会话对应的历史文件路径"""
    ensure_dirs()
    return HISTORY_DIR / f"{session_id}.jsonl"


def load_llm_config() -> Dict[str, Any]:
    """读取 llm_config.json，供前端模型选择使用。"""
    if not LLM_CONFIG_FILE.exists():
        return {"providers": [], "defaults": {}}
    with LLM_CONFIG_FILE.open("r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"providers": [], "defaults": {}}


# 系统提示词配置文件
SYSTEM_PROMPT_FILE = Path(__file__).parent / "config" / "system_prompt.json"

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


def timestamp():
    return datetime.utcnow().isoformat() + "Z"


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
    
    # 如果指定了 session_id，读取该会话文件
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

    # 未指定 session_id，返回所有会话的列表
    sessions = []
    for file in HISTORY_DIR.glob("*.jsonl"):
        session_id = file.stem
        # 读取文件获取第一条消息作为标题，最后修改时间作为排序依据
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
                        first_user_msg = rec.get("content", "")[:50]  # 截取前50字符作为标题
                except json.JSONDecodeError:
                    continue
        
        sessions.append({
            "session_id": session_id,
            "title": first_user_msg or "新对话",
            "timestamp": last_timestamp,
            "updated_at": file.stat().st_mtime
        })
    
    # 按更新时间倒序排列
    sessions.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
    return sessions[:limit]


# ---- ASR (Baidu) ----
def baidu_get_token() -> str:
    cfg = get_asr_model_config() if get_asr_model_config else {}
    ak = cfg.get("baidu_api_key")
    sk = cfg.get("baidu_secret_key")
    token_url = cfg.get("baidu_token_url") or "https://aip.baidubce.com/oauth/2.0/token"
    if not ak or not sk:
        raise RuntimeError("缺少百度 ASR 的 API Key/Secret Key，请在 config.py 的 get_asr_model_config 中配置")
    params = {"grant_type": "client_credentials", "client_id": ak, "client_secret": sk}
    resp = requests.post(token_url, params=params, timeout=10)
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"获取百度 ASR token 失败: {data}")
    return data["access_token"]


def baidu_asr(audio_bytes: bytes, fmt: str = "wav", rate: int = 16000, channel: int = 1) -> str:
    token = baidu_get_token()
    server_url = "https://vop.baidu.com/server_api"
    speech_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    payload = {
        "format": fmt,
        "rate": rate,
        "channel": channel,
        "cuid": "chat-ui",
        "token": token,
        "len": len(audio_bytes),
        "speech": speech_b64,
    }
    headers = {"Content-Type": "application/json"}
    resp = requests.post(server_url, headers=headers, data=json.dumps(payload), timeout=15)
    data = resp.json()
    if data.get("err_no") != 0:
        raise RuntimeError(f"百度 ASR 失败: {data}")
    result = data.get("result") or []
    return result[0] if result else ""


def call_llm(
    user_message: str,
    model: str,
    system_prompt: str,
    api_key: str,
    base_url: str,
    provider_id: str,
) -> str:
    """调用 OpenAI 兼容接口的模型。"""
    is_local = (provider_id or "").startswith("local")
    if not api_key and not is_local:
        raise ValueError("缺少 API Key，请在设置中填写。")

    resolved_base = base_url or DEFAULT_BASE_URLS.get(provider_id) or None
    # 本地模型/服务若不需要鉴权，用一个空字符串占位即可
    client = OpenAI(api_key=api_key or "", base_url=resolved_base)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=False,
    )
    if not completion.choices:
        raise RuntimeError("模型未返回结果")
    return completion.choices[0].message.content


@app.route('/ui/<path:filename>')
def serve_ui(filename):
    return send_from_directory('ui', filename)


@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route('/voice_data/<path:filename>')
def serve_voice_data(filename):
    return send_from_directory(VOICE_DATA_DIR, filename)


@app.route('/favicon.ico')
def favicon():
    # 提供站点图标，若无文件则返回 204 避免 404 噪声
    if FAVICON_FILE.exists():
        return send_from_directory(BASE_DIR, 'favicon.ico')
    return ("", 204)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    处理前端发来的聊天请求
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        user_message = (data.get('message') or '').strip()

        # 获取配置参数
        model = data.get('model', None)
        system_prompt = data.get('system_prompt', '')
        api_key = data.get('api_key', '')
        base_url = data.get('base_url', '')
        provider_id = data.get('provider_id', None)
        session_id = data.get('session_id', None)

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        print(f"收到前端消息: {user_message}")
        print(f"配置信息: Model={model}, Provider={provider_id}, Session={session_id}")

        if call_model is None:
            return jsonify({'error': '后端未正确加载 llm_runner，请检查导入'}), 500

        try:
            bot_response = call_model(
                message=user_message,
                provider_id=provider_id,
                model_id=model,
                system_prompt=system_prompt,
                api_key=api_key or None,
                base_url=base_url or None,
            )
        except Exception as e:
            print(f"LLM 调用失败: {e}")
            return jsonify({'error': f'LLM 调用失败: {e}'}), 500

        meta = {"type": "chat", "model": model, "provider": provider_id}
        append_history("user", user_message, meta, session_id=session_id)
        append_history("assistant", bot_response, meta, session_id=session_id)

        return jsonify({'response': bot_response})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat_stream', methods=['POST'])
def chat_stream():
    """流式输出接口，逐段返回文本。"""
    import logging
    from datetime import datetime
    
    # 配置日志
    log_dir = Path(__file__).parent / "log"
    log_dir.mkdir(exist_ok=True)
    chat_log = log_dir / "chat.log"
    
    def log_msg(msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {msg}\n"
        with open(chat_log, 'a', encoding='utf-8') as f:
            f.write(log_line)
        print(log_line.strip())
    
    try:
        data = request.get_json(force=True, silent=True) or {}
        user_message = (data.get('message') or '').strip()
        # 用于历史记录的原始消息（不含知识库参考资料）
        original_message = (data.get('original_message') or user_message).strip()
        model = data.get('model', None)
        # 优先使用后端配置的系统提示词，前端传的作为备选
        system_prompt = get_system_prompt() or data.get('system_prompt', '')
        api_key = data.get('api_key', '')
        base_url = data.get('base_url', '')
        provider_id = data.get('provider_id', None)
        session_id = data.get('session_id', None)
        # 知识库来源信息
        kb_sources = data.get('kb_sources', [])
        # 思考模式
        enable_thinking = data.get('enable_thinking', False)
        # Prompt 引擎相关参数
        enable_prompt_engine = data.get('enable_prompt_engine', True)  # 默认启用
        scenario_type = data.get('scenario_type')  # 可选：指定场景类型
        # 联网搜索参数
        enable_web_search = data.get('enable_web_search', False)  # 是否启用联网搜索
        web_search_query = data.get('web_search_query', '')  # 自定义搜索关键词（可选）
        
        log_msg(f"[chat_stream] 收到请求 - 思考模式: {enable_thinking}, 模型: {model}, provider: {provider_id}")
        log_msg(f"[chat_stream] 联网搜索: {enable_web_search}")
        log_msg(f"[chat_stream] 系统提示词: {system_prompt[:50] if system_prompt else '(空)'}")
        log_msg(f"[chat_stream] 用户消息: {original_message[:100]}...")

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        if call_model_stream is None:
            return jsonify({'error': '后端未正确加载 llm_runner，请检查导入'}), 500

        # 不再使用场景检测功能
        enhanced_message = user_message
        detected_scenario = None
        
        # 联网搜索功能
        web_search_context = ""
        web_search_results = []
        if enable_web_search and WEB_SEARCH_AVAILABLE:
            try:
                # 使用自定义搜索词或用户消息作为搜索关键词
                search_query = web_search_query if web_search_query else user_message
                log_msg(f"[chat_stream] 开始联网搜索: {search_query}")
                
                search_result = search_and_format(search_query, max_results=5)
                
                if search_result["success"]:
                    web_search_context = search_result["formatted_text"]
                    web_search_results = search_result["raw_data"]
                    log_msg(f"[chat_stream] 联网搜索成功，找到 {len(web_search_results)} 条结果")
                    
                    # 将搜索结果添加到用户消息中
                    enhanced_message = f"{web_search_context}\n\n用户问题: {user_message}\n\n请根据以上搜索到的信息回答用户的问题。"
                else:
                    log_msg(f"[chat_stream] 联网搜索失败: {search_result.get('error', '未知错误')}")
                    
            except Exception as e:
                log_msg(f"[chat_stream] 联网搜索异常: {e}")
                import traceback
                traceback.print_exc()

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        if call_model_stream is None:
            return jsonify({'error': '后端未正确加载 llm_runner，请检查导入'}), 500

        def generate():
            full = []
            try:
                log_msg(f"[chat_stream] 开始调用模型，enable_thinking={enable_thinking}")
                # 使用增强后的消息
                for chunk in call_model_stream(
                    message=enhanced_message,
                    provider_id=provider_id,
                    model_id=model,
                    system_prompt=system_prompt,
                    api_key=api_key or None,
                    base_url=base_url or None,
                    enable_thinking=enable_thinking,
                ):
                    if chunk:
                        full.append(chunk)
                        yield chunk
                # 生成结束后写入历史（使用原始消息）
                bot_resp = "".join(full)
                log_msg(f"[chat_stream] 模型输出完成，长度: {len(bot_resp)}, 包含<think>: {'<think>' in bot_resp}")
                meta = {"type": "chat", "model": model, "provider": provider_id}
                # 如果使用了 Prompt 引擎，记录场景信息
                if detected_scenario:
                    meta["scenario"] = detected_scenario
                # 如果使用了联网搜索，记录搜索信息
                if enable_web_search and web_search_results:
                    meta["web_search"] = True
                    meta["search_query"] = web_search_query or user_message
                append_history("user", original_message, meta, session_id=session_id)
                # 保存助手回复时包含知识库来源和联网搜索结果
                bot_meta = {"type": "chat", "model": model, "provider": provider_id}
                if kb_sources:
                    bot_meta["kb_sources"] = kb_sources
                if detected_scenario:
                    bot_meta["scenario"] = detected_scenario
                if enable_web_search and web_search_results:
                    bot_meta["web_search_results"] = web_search_results
                append_history("assistant", bot_resp, bot_meta, session_id=session_id)
            except Exception as e:
                log_msg(f"[chat_stream] 流式调用失败: {e}")
                yield f"[ERROR]{e}"

        return Response(stream_with_context(generate()), mimetype='text/plain')

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/llm_config', methods=['GET'])
def api_llm_config():
    """返回 llm_config.json 内容，供前端模型选择使用。"""
    return jsonify(load_llm_config())


@app.route('/api/system_prompt', methods=['GET'])
def api_get_system_prompt():
    """获取系统提示词配置"""
    config = load_system_prompt_config()
    return jsonify(config)


@app.route('/api/system_prompt', methods=['POST'])
def api_set_system_prompt():
    """设置系统提示词"""
    data = request.get_json(force=True, silent=True) or {}
    config = load_system_prompt_config()
    
    if 'default' in data:
        config['default'] = data['default']
    if 'presets' in data:
        config['presets'] = data['presets']
    
    save_system_prompt_config(config)
    return jsonify({"success": True, "config": config})


@app.route('/api/env/config', methods=['GET'])
def api_get_env_config():
    """获取 .env 文件中的 API 配置"""
    try:
        # 从环境变量读取配置
        config = {
            'qwen': {
                'api_key': os.getenv('ALI_API_KEY', ''),
                'base_url': os.getenv('ALI_BASE_URL', ''),
                'has_config': bool(os.getenv('ALI_API_KEY'))
            },
            'openai': {
                'api_key': os.getenv('OPENAI_API_KEY', ''),
                'base_url': os.getenv('OPENAI_BASE_URL', ''),
                'has_config': bool(os.getenv('OPENAI_API_KEY'))
            },
            'volcengine': {
                'api_key': os.getenv('ARK_API_KEY', ''),
                'base_url': os.getenv('APK_BASE_URL', ''),
                'has_config': bool(os.getenv('ARK_API_KEY'))
            },
            'deepseek': {
                'api_key': os.getenv('DEEPSEEK_API_KEY', ''),
                'base_url': os.getenv('DEEPSEEK_BASE_URL', ''),
                'has_config': bool(os.getenv('DEEPSEEK_API_KEY'))
            },
            'local': {
                'api_key': os.getenv('LOCAL_API_KEY', ''),
                'base_url': os.getenv('LOCAL_LLM_BASE_URL', ''),
                'has_config': bool(os.getenv('LOCAL_LLM_BASE_URL'))
            }
        }
        
        return jsonify({
            'success': True,
            'config': config
        })
        
    except Exception as e:
        print(f"读取环境配置失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/web_search', methods=['POST'])
def api_web_search():
    """联网搜索 API"""
    if not WEB_SEARCH_AVAILABLE:
        return jsonify({
            'success': False,
            'error': '联网搜索功能未启用，请检查 web_search 模块'
        }), 500
    
    try:
        data = request.get_json(force=True, silent=True) or {}
        query = data.get('query', '').strip()
        max_results = data.get('max_results', 5)
        
        if not query:
            return jsonify({
                'success': False,
                'error': '缺少搜索关键词'
            }), 400
        
        # 执行搜索
        result = search_and_format(query, max_results=max_results)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"联网搜索失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/web_search/status', methods=['GET'])
def api_web_search_status():
    """检查联网搜索功能状态"""
    return jsonify({
        'available': WEB_SEARCH_AVAILABLE,
        'api_key_configured': bool(os.getenv('METASO_API_KEY'))
    })


@app.route('/api/scenario/prompt', methods=['GET'])
def api_get_scenario_prompt():
    """获取指定场景的提示词"""
    scenario = request.args.get('scenario')
    
    if not scenario:
        return jsonify({'error': '缺少 scenario 参数'}), 400
    
    if not PROMPT_ENGINE_AVAILABLE or not get_prompt_engine:
        return jsonify({'error': 'Prompt 引擎未加载'}), 500
    
    try:
        from prompt_engine import ScenarioType
        
        # 场景类型映射
        scenario_map = {
            'operation_guide': ScenarioType.OPERATION_GUIDE,
            'fault_diagnosis': ScenarioType.FAULT_DIAGNOSIS,
            'safety_regulation': ScenarioType.SAFETY_REGULATION,
            'code_debug': ScenarioType.CODE_DEBUG
        }
        
        if scenario not in scenario_map:
            return jsonify({'error': '无效的场景类型'}), 400
        
        # 先尝试从配置文件读取自定义提示词
        config = load_system_prompt_config()
        custom_prompt = None
        
        if 'scenario_prompts' in config and scenario in config['scenario_prompts']:
            custom_prompt = config['scenario_prompts'][scenario].get('prompt')
        
        # 如果有自定义提示词，使用自定义的；否则使用默认的
        if custom_prompt:
            prompt = custom_prompt
        else:
            # 获取默认提示词
            engine = get_prompt_engine()
            prompt = engine.generate_prompt(scenario_map[scenario])
        
        return jsonify({
            'success': True,
            'scenario': scenario,
            'prompt': prompt,
            'is_custom': bool(custom_prompt)
        })
        
    except Exception as e:
        print(f"获取场景提示词失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/scenario/prompt', methods=['POST'])
def api_save_scenario_prompt():
    """保存指定场景的提示词"""
    data = request.get_json(force=True, silent=True) or {}
    scenario = data.get('scenario')
    prompt = data.get('prompt')
    
    if not scenario or prompt is None:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        # 保存到配置文件
        config = load_system_prompt_config()
        
        if 'scenario_prompts' not in config:
            config['scenario_prompts'] = {}
        
        config['scenario_prompts'][scenario] = {
            'prompt': prompt,
            'updated_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        save_system_prompt_config(config)
        
        return jsonify({
            'success': True,
            'message': '提示词已保存'
        })
        
    except Exception as e:
        print(f"保存场景提示词失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/scenario/prompt/default', methods=['GET'])
def api_get_default_scenario_prompt():
    """获取指定场景的默认提示词"""
    scenario = request.args.get('scenario')
    
    if not scenario:
        return jsonify({'error': '缺少 scenario 参数'}), 400
    
    if not PROMPT_ENGINE_AVAILABLE or not get_prompt_engine:
        return jsonify({'error': 'Prompt 引擎未加载'}), 500
    
    try:
        from prompt_engine import ScenarioType
        
        # 场景类型映射
        scenario_map = {
            'operation_guide': ScenarioType.OPERATION_GUIDE,
            'fault_diagnosis': ScenarioType.FAULT_DIAGNOSIS,
            'safety_regulation': ScenarioType.SAFETY_REGULATION,
            'code_debug': ScenarioType.CODE_DEBUG
        }
        
        if scenario not in scenario_map:
            return jsonify({'error': '无效的场景类型'}), 400
        
        # 获取默认提示词（直接从引擎生成，不读取配置）
        engine = get_prompt_engine()
        prompt = engine.generate_prompt(scenario_map[scenario])
        
        return jsonify({
            'success': True,
            'scenario': scenario,
            'prompt': prompt
        })
        
    except Exception as e:
        print(f"获取默认场景提示词失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        limit_raw = request.args.get('limit', 50)
        limit = int(limit_raw)
        session_id = request.args.get('session_id')
    except ValueError:
        limit = 50
        session_id = None
    records = read_history(limit, session_id=session_id)
    return jsonify({"history": records})


@app.route('/api/session/new', methods=['POST'])
def new_session():
    """创建新会话，返回新的 session_id"""
    session_id = str(uuid.uuid4())
    return jsonify({"session_id": session_id})


@app.route('/api/session/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """删除指定会话"""
    session_file = get_session_file(session_id)
    if session_file.exists():
        session_file.unlink()
        return jsonify({"success": True, "message": "会话已删除"})
    return jsonify({"success": False, "message": "会话不存在"}), 404


@app.route('/api/upload', methods=['POST'])
def upload():
    """上传文件接口，支持文档/图片/视频"""
    if 'file' not in request.files:
        return jsonify({"error": "缺少上传文件"}), 400
    
    file = request.files['file']
    original_filename = file.filename or ""
    ext = Path(original_filename).suffix.lower()
    
    # 验证文件类型
    allowed_exts = {'.docx', '.txt', '.pdf', '.md', '.html', '.csv', '.xlsx',
                    '.jpg', '.jpeg', '.png', '.mp4', '.avi', '.mov', '.flv'}
    if ext not in allowed_exts:
        return jsonify({"error": f"不支持的文件类型: {ext}"}), 400
    
    # 保留原始文件名（支持中文）
    safe_name = safe_filename(original_filename)
    if not safe_name:
        safe_name = f"file_{uuid.uuid4().hex}{ext}"
    
    ensure_dirs()
    save_path = UPLOAD_DIR / safe_name
    
    # 检查文件大小
    file.seek(0, 2)  # 移到文件末尾
    file_size = file.tell()
    file.seek(0)  # 移回开头
    
    # 大小限制
    size_limits = {
        'document': 50 * 1024 * 1024,  # 50MB
        'image': 10 * 1024 * 1024,     # 10MB
        'video': 50 * 1024 * 1024,     # 50MB
    }
    
    if ext in {'.jpg', '.jpeg', '.png'}:
        category = 'image'
    elif ext in {'.mp4', '.avi', '.mov', '.flv'}:
        category = 'video'
    else:
        category = 'document'
    
    if file_size > size_limits[category]:
        limit_mb = size_limits[category] / (1024 * 1024)
        return jsonify({"error": f"文件大小超过限制 ({limit_mb}MB)"}), 400
    
    # 保存文件
    file.save(save_path)
    
    file_url = f"/uploads/{safe_name}"
    return jsonify({
        "success": True,
        "filename": safe_name,
        "file_url": file_url,
        "size": file_size,
        "category": category
    })


@app.route('/api/upload_and_parse', methods=['POST'])
def upload_and_parse():
    """上传并解析文件，返回解析后的内容"""
    if 'file' not in request.files:
        return jsonify({"error": "缺少上传文件"}), 400
    
    file = request.files['file']
    original_filename = file.filename or ""
    ext = Path(original_filename).suffix.lower()
    
    # 保留原始文件名（支持中文）
    safe_name = safe_filename(original_filename)
    if not safe_name:
        safe_name = f"file_{uuid.uuid4().hex}{ext}"
    
    ensure_dirs()
    save_path = UPLOAD_DIR / safe_name
    file.save(save_path)
    
    # 解析文件
    if parse_file is None:
        return jsonify({"error": "解析服务未加载"}), 500
    
    result = parse_file(str(save_path))
    
    if not result['success']:
        return jsonify({"error": result['error']}), 400
    
    return jsonify({
        "success": True,
        "filename": safe_name,
        "file_url": f"/uploads/{safe_name}",
        "type": result['type'],
        "content": result['content'] if result['type'] == 'text' else None,
        "media_info": result['content'] if result['type'] in ('image', 'video') else None
    })


@app.route('/api/chat_with_file', methods=['POST'])
def chat_with_file():
    """带文件的聊天接口（流式），支持文本和图片多模态"""
    if call_model_stream is None:
        return jsonify({'error': '后端未正确加载 llm_runner'}), 500
    
    # 获取文件和消息
    file = request.files.get('file')
    message = request.form.get('message', '').strip()
    model = request.form.get('model')
    system_prompt = request.form.get('system_prompt', '')
    api_key = request.form.get('api_key', '')
    base_url = request.form.get('base_url', '')
    provider_id = request.form.get('provider_id')
    session_id = request.form.get('session_id')
    
    if not file and not message:
        return jsonify({'error': '请提供文件或消息'}), 400
    
    # 处理文件
    final_message = message  # 默认使用用户消息
    is_multimodal = False
    saved_filename = None
    image_file_path = None  # 保存图片路径，用于本地多模态模型
    is_local_vl_provider = False

    # 仅本地多模态模型需要单独传 image_path，远程多模态需要传完整 messages_list
    if provider_id:
        cfg = load_llm_config()
        for provider in cfg.get("providers", []):
            if provider.get("id") == provider_id:
                is_local_vl_provider = provider.get("client") == "local_vl"
                break
    
    if file:
        original_filename = file.filename or ""
        ext = Path(original_filename).suffix.lower()
        # 保留原始文件名（支持中文）
        safe_name = safe_filename(original_filename)
        
        # 如果文件名为空，使用 UUID 生成
        if not safe_name or not Path(safe_name).suffix:
            safe_name = f"file_{uuid.uuid4().hex}{ext}"
        
        saved_filename = safe_name
        
        ensure_dirs()
        save_path = UPLOAD_DIR / safe_name
        file.save(save_path)
        
        # 如果是图片，保存路径用于本地多模态模型
        if ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}:
            image_file_path = str(save_path)
        
        print(f"[chat_with_file] 文件已保存: {save_path}, 扩展名: {ext}")
        
        if parse_for_chat:
            result = parse_for_chat(str(save_path), message)
            print(f"[chat_with_file] parse_for_chat 结果: success={result.get('success')}, error={result.get('error')}")
            
            if result['success']:
                messages_list = result.get('messages', [])
                print(f"[chat_with_file] messages_list 长度: {len(messages_list)}")
                
                # 检查是否包含图片（多模态消息）
                has_image = any(
                    msg.get('type') == 'image_url' 
                    for msg in messages_list
                )
                
                if has_image:
                    # 多模态消息：直接使用 parse_for_chat 返回的消息列表
                    is_multimodal = True
                    final_message = messages_list
                    print(f"[chat_with_file] 多模态消息")
                elif messages_list and messages_list[0].get('type') == 'text':
                    # 纯文本消息
                    final_message = messages_list[0].get('text', '')
                    print(f"[chat_with_file] 文本消息，长度: {len(final_message)}")
            else:
                print(f"[chat_with_file] 解析失败: {result.get('error')}")
                return jsonify({'error': f"文件解析失败: {result.get('error')}"}), 400
        else:
            print("[chat_with_file] parse_for_chat 未加载")
            return jsonify({'error': '文件解析服务未加载'}), 500
    
    if not final_message:
        print(f"[chat_with_file] final_message 为空")
        return jsonify({'error': '无法解析文件内容'}), 400
    
    def generate():
        full = []
        try:
            # 本地多模态模型使用原始文本 + image_path；远程多模态模型使用 parse_for_chat 返回的消息列表
            request_message = message if is_local_vl_provider else final_message
            for chunk in call_model_stream(
                message=request_message,
                provider_id=provider_id,
                model_id=model,
                system_prompt=system_prompt,
                api_key=api_key or None,
                base_url=base_url or None,
                image_path=image_file_path if is_local_vl_provider else None,
            ):
                if chunk:
                    full.append(chunk)
                    yield chunk
            
            # 写入历史
            bot_resp = "".join(full)
            meta = {"type": "chat_with_file", "model": model, "provider": provider_id}
            if saved_filename:
                meta["filename"] = saved_filename
                meta["file_url"] = f"/uploads/{saved_filename}"
            if session_id:
                user_msg = message or ("[图片]" if is_multimodal else "[文件]")
                append_history("user", user_msg, meta, session_id=session_id)
                append_history("assistant", bot_resp, meta, session_id=session_id)
        except Exception as e:
            print(f"流式调用失败: {e}")
            yield f"[ERROR]{e}"
    
    return Response(stream_with_context(generate()), mimetype='text/plain')


@app.route('/api/asr', methods=['POST'])
def asr():
    """语音识别接口"""
    if 'file' not in request.files:
        return jsonify({"error": "缺少音频文件"}), 400
    
    file = request.files['file']
    provider_id = request.form.get('provider_id')  # 可选，指定 ASR provider
    
    # 获取原始文件名和扩展名
    original_filename = file.filename or ""
    original_ext = Path(original_filename).suffix.lower() or '.webm'
    
    filename = safe_filename(original_filename) or f"audio_{uuid.uuid4().hex}{original_ext}"
    ensure_dirs()
    save_path = VOICE_DATA_DIR / filename
    file.save(save_path)
    
    fmt = (filename.rsplit('.', 1)[-1] if '.' in filename else 'wav').lower()
    actual_path = save_path  # 实际用于识别的文件路径
    
    print(f"[ASR] 收到音频文件: {filename}, 格式: {fmt}, provider: {provider_id}")
    
    # 对于非 wav/pcm 格式，尝试转换为 wav（百度 ASR 只支持 wav/pcm）
    need_convert = fmt not in ('wav', 'pcm')
    
    if need_convert and convert_to_wav:
        print(f"[ASR] 转换音频格式: {fmt} -> wav")
        wav_path = str(save_path.with_suffix('.wav'))
        success, result = convert_to_wav(str(save_path), wav_path)
        if success:
            actual_path = Path(result)
            fmt = 'wav'
            print(f"[ASR] 转换成功: {result}")
        else:
            print(f"[ASR] 转换失败: {result}，尝试用原格式继续")
    elif need_convert:
        print(f"[ASR] 需要转换但 convert_to_wav 不可用，请安装 ffmpeg")
    
    try:
        if asr_recognize:
            # 使用统一的 ASR runner
            transcript = asr_recognize(str(actual_path), provider_id=provider_id, format=fmt)
        else:
            # 回退到旧的百度 ASR（需要 wav 格式）
            if fmt != 'wav':
                return jsonify({"error": f"百度 ASR 不支持 {fmt} 格式，请安装 ffmpeg 进行格式转换"}), 400
            
            audio_bytes = actual_path.read_bytes()
            transcript = baidu_asr(audio_bytes, fmt=fmt)
    except Exception as e:
        print(f"ASR 失败: {e}")
        return jsonify({"error": f"ASR 失败: {e}"}), 500

    meta = {"type": "asr", "filename": filename, "file_url": f"/voice_data/{filename}"}
    append_history("assistant", f"语音转写：{transcript}", meta)

    return jsonify({
        "text": transcript,
        "file_url": meta["file_url"],
        "meta": meta
    })


@app.route('/api/tts', methods=['POST'])
def tts():
    """语音合成接口"""
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get('text') or '').strip()
    provider_id = data.get('provider_id')  # 可选，指定 TTS provider
    
    if not text:
        return jsonify({"error": "缺少待合成的文本"}), 400

    ensure_dirs()
    audio_name = f"tts_{uuid.uuid4().hex}.mp3"
    audio_path = UPLOAD_DIR / audio_name
    
    try:
        if tts_synthesize:
            # 使用统一的 TTS runner
            audio_bytes = tts_synthesize(
                text,
                output_path=str(audio_path),
                provider_id=provider_id,
                spd=data.get('spd', 5),
                pit=data.get('pit', 5),
                vol=data.get('vol', 5),
                per=data.get('per', 0),
            )
        else:
            # 回退：写入占位文件
            audio_path = UPLOAD_DIR / f"tts_{uuid.uuid4().hex}.txt"
            audio_path.write_text(f"TTS 未配置，原文：{text}", encoding="utf-8")
    except Exception as e:
        print(f"TTS 失败: {e}")
        return jsonify({"error": f"TTS 失败: {e}"}), 500

    audio_url = f"/uploads/{audio_name}"
    meta = {"type": "tts", "audio_url": audio_url}
    append_history("assistant", f"已生成语音：{text[:60]}", meta)

    return jsonify({"audio_url": audio_url, "meta": meta})


@app.route('/api/ocr', methods=['POST'])
def ocr():
    """OCR 文字识别接口"""
    if 'file' not in request.files:
        return jsonify({"error": "缺少图片文件"}), 400
    
    file = request.files['file']
    provider_id = request.form.get('provider_id')  # 可选，指定 OCR provider
    
    filename = safe_filename(file.filename) or f"ocr_{uuid.uuid4().hex}.png"
    ensure_dirs()
    save_path = UPLOAD_DIR / filename
    file.save(save_path)
    
    try:
        if ocr_recognize:
            text = ocr_recognize(str(save_path), provider_id=provider_id)
        else:
            return jsonify({"error": "OCR 服务未配置"}), 500
    except Exception as e:
        print(f"OCR 失败: {e}")
        return jsonify({"error": f"OCR 失败: {e}"}), 500

    return jsonify({
        "text": text,
        "file_url": f"/uploads/{filename}"
    })


# ==================== 知识库 API ====================

def get_kb_instance(kb_type: str):
    """获取或创建知识库实例"""
    if not KB_AVAILABLE:
        return None
    
    kb_folder = KB_TYPE_MAP.get(kb_type, kb_type)
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
            kb = FaultDiagnosisKnowledgeBase(
                data_dir=str(kb_dir),
                chunk_method="smart",  # 使用智能切分
                chunk_size=500,
                device=None  # 自动检测 GPU
            )
            # 加载已有索引
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
    kb_folder = KB_TYPE_MAP.get(kb_type, kb_type)
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
    kb_folder = KB_TYPE_MAP.get(kb_type, kb_type)
    kb_data_dir = KB_BASE_DIR / kb_folder / "data"
    kb_data_dir.mkdir(parents=True, exist_ok=True)
    json_path = kb_data_dir / "text.json"
    
    data["last_updated"] = timestamp()
    with json_path.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.route('/api/kb/files', methods=['GET'])
def kb_list_files():
    """获取知识库文件列表，从 text.json 读取"""
    kb_type = request.args.get('type', 'guide')
    kb_folder = KB_TYPE_MAP.get(kb_type, kb_type)
    kb_data_dir = KB_BASE_DIR / kb_folder / "data"
    
    if not kb_data_dir.exists():
        return jsonify({"success": True, "files": [], "index_built": False, "total_chunks": 0})
    
    # 从 text.json 读取文件信息
    kb_data = load_kb_json(kb_type)
    files_in_json = {f['name']: f for f in kb_data.get('files', [])}
    
    # 检查索引文件是否真实存在
    index_file = KB_BASE_DIR / kb_folder / "index" / "index.pkl"
    actual_index_built = index_file.exists()
    
    # 如果 JSON 中说索引已构建，但实际文件不存在，更新状态
    if kb_data.get('index_built', False) and not actual_index_built:
        print(f"[KB] 检测到索引文件已删除，更新状态: {kb_type}")
        kb_data['index_built'] = False
        kb_data['total_chunks'] = 0
        save_kb_json(kb_type, kb_data)
        # 清除缓存的实例
        if kb_type in _kb_instances:
            del _kb_instances[kb_type]
    
    # 同步实际文件系统中的文件
    actual_files = []
    for file_path in kb_data_dir.iterdir():
        if file_path.is_file() and file_path.name != 'text.json':
            stat = file_path.stat()
            
            # 如果 JSON 中有该文件的信息，使用 JSON 中的数据
            if file_path.name in files_in_json:
                file_info = files_in_json[file_path.name].copy()
                # 更新文件大小（可能有变化）
                file_info['size'] = f"{stat.st_size / 1024:.1f}KB" if stat.st_size < 1024*1024 else f"{stat.st_size / (1024*1024):.1f}MB"
            else:
                # 新文件，创建默认信息
                file_info = {
                    "id": str(uuid.uuid4())[:8],
                    "name": file_path.name,
                    "type": "文档",
                    "size": f"{stat.st_size / 1024:.1f}KB" if stat.st_size < 1024*1024 else f"{stat.st_size / (1024*1024):.1f}MB",
                    "chars": 0,
                    "recall": 0,
                    "date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "enabled": True,
                    "status": "pending",
                    "batch": datetime.fromtimestamp(stat.st_mtime).strftime("%Y%m%d%H%M")
                }
            
            actual_files.append(file_info)
    
    # 更新 text.json
    kb_data['files'] = actual_files
    save_kb_json(kb_type, kb_data)
    
    return jsonify({
        "success": True,
        "files": actual_files,
        "index_built": kb_data.get('index_built', False),
        "total_chunks": kb_data.get('total_chunks', 0)
    })


@app.route('/api/kb/upload', methods=['POST'])
def kb_upload_files():
    """上传文件到知识库"""
    kb_type = request.form.get('kb_type', 'guide')
    kb_folder = KB_TYPE_MAP.get(kb_type, kb_type)
    kb_data_dir = KB_BASE_DIR / kb_folder / "data"
    kb_data_dir.mkdir(parents=True, exist_ok=True)
    
    files = request.files.getlist('files')
    if not files:
        return jsonify({"success": False, "error": "没有上传文件"}), 400
    
    # 加载现有的 text.json
    kb_data = load_kb_json(kb_type)
    existing_files = {f['name']: f for f in kb_data.get('files', [])}
    
    uploaded = []
    for file in files:
        if file.filename:
            # 保留中文文件名，只替换危险字符
            original_name = file.filename
            # 移除路径分隔符和其他危险字符
            safe_name = original_name.replace('/', '_').replace('\\', '_').replace('..', '_')
            safe_name = safe_name.strip()
            if not safe_name:
                safe_name = f"file_{uuid.uuid4().hex}{Path(original_name).suffix}"
            save_path = kb_data_dir / safe_name
            file.save(save_path)
            uploaded.append(safe_name)
            
            # 添加到 text.json
            stat = save_path.stat()
            if safe_name not in existing_files:
                existing_files[safe_name] = {
                    "id": str(uuid.uuid4())[:8],
                    "name": safe_name,
                    "type": "文档",
                    "size": f"{stat.st_size / 1024:.1f}KB" if stat.st_size < 1024*1024 else f"{stat.st_size / (1024*1024):.1f}MB",
                    "chars": 0,
                    "recall": 0,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "enabled": True,
                    "status": "pending",
                    "batch": datetime.now().strftime("%Y%m%d%H%M")
                }
    
    # 保存更新后的 text.json
    kb_data['files'] = list(existing_files.values())
    kb_data['index_built'] = False  # 上传新文件后需要重新构建索引
    save_kb_json(kb_type, kb_data)
    
    return jsonify({"success": True, "uploaded": uploaded, "message": f"已上传 {len(uploaded)} 个文件"})


@app.route('/api/kb/build', methods=['POST'])
def kb_build_index():
    """构建知识库索引"""
    if not KB_AVAILABLE:
        return jsonify({"success": False, "error": "知识库模块未加载"}), 500
    
    data = request.get_json(force=True, silent=True) or {}
    kb_type = data.get('kb_type', 'guide')
    chunk_method = data.get('chunk_method', 'smart')  # 默认使用智能切分
    chunk_size = int(data.get('chunk_size', 500))
    
    kb_folder = KB_TYPE_MAP.get(kb_type, kb_type)
    kb_dir = KB_BASE_DIR / kb_folder
    
    try:
        # 清除缓存的实例
        if kb_type in _kb_instances:
            del _kb_instances[kb_type]
        
        # 读取 text.json 获取启用的文件列表
        kb_data = load_kb_json(kb_type)
        enabled_files = [
            f['name'] for f in kb_data.get('files', [])
            if f.get('enabled', True)
        ]
        
        print(f"[KB] 启用的文件列表: {enabled_files}")
        print(f"[KB] 知识库目录: {kb_dir}")
        print(f"[KB] 数据目录: {kb_dir / 'data'}")
        
        if not enabled_files:
            return jsonify({"success": False, "error": "没有启用的文件"}), 400
        
        kb = FaultDiagnosisKnowledgeBase(
            data_dir=str(kb_dir),
            chunk_method=chunk_method,
            chunk_size=chunk_size,
            device=None  # 自动检测 GPU
        )
        
        # 需要传递 source_dir 参数
        source_dir = str(kb_dir / 'data')
        print(f"[KB] 调用 build_index，source_dir={source_dir}, enabled_files={enabled_files}")
        kb.build_index(source_dir=source_dir, enabled_files=enabled_files)
        _kb_instances[kb_type] = kb
        
        total_chunks = kb.vector_store.index.ntotal if kb.vector_store else 0
        
        # 更新 text.json 中的状态
        kb_data['index_built'] = True
        kb_data['total_chunks'] = total_chunks
        
        # 统计每个文件的字符数和块数
        file_stats = {}
        if kb.vector_store and hasattr(kb.vector_store, 'metadata'):
            for metadata in kb.vector_store.metadata:
                source = metadata.get('source', '')
                if source:
                    if source not in file_stats:
                        file_stats[source] = {'chars': 0, 'chunks': 0}
                    file_stats[source]['chars'] += metadata.get('length', 0)
                    file_stats[source]['chunks'] += 1
        
        # 更新文件信息
        for file_info in kb_data.get('files', []):
            filename = file_info['name']
            if file_info.get('enabled', True):
                file_info['status'] = 'completed'
                # 更新字符数
                if filename in file_stats:
                    file_info['chars'] = file_stats[filename]['chars']
                    file_info['chunks'] = file_stats[filename]['chunks']
            else:
                file_info['status'] = 'pending'
        
        save_kb_json(kb_type, kb_data)
        
        return jsonify({
            "success": True,
            "message": "索引构建完成",
            "total_docs": total_chunks
        })
    except Exception as e:
        print(f"[KB] 构建索引失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/kb/search', methods=['POST'])
def kb_search():
    """知识库检索"""
    if not KB_AVAILABLE:
        return jsonify({"success": False, "error": "知识库模块未加载"}), 500
    
    data = request.get_json(force=True, silent=True) or {}
    query = (data.get('query') or '').strip()
    kb_type = data.get('kb_type', 'guide')
    top_k = int(data.get('top_k', 5))
    threshold = float(data.get('threshold', 0.0))
    use_rewrite = data.get('use_rewrite', False)  # 是否启用查询改写
    
    if not query:
        return jsonify({"success": False, "error": "查询内容不能为空"}), 400
    
    kb = get_kb_instance(kb_type)
    if not kb:
        return jsonify({"success": False, "error": f"知识库 {kb_type} 未加载或不存在"}), 404
    
    try:
        # 查询改写
        rewritten_query = query
        if use_rewrite:
            try:
                from models.LLM.query_rewriter import rewrite_query
                rewritten_query = rewrite_query(query)
                log_msg = f"[KB] 查询改写: '{query}' -> '{rewritten_query}'"
                print(log_msg)
                # 写入日志文件
                log_dir = Path(__file__).parent / "log"
                log_dir.mkdir(exist_ok=True)
                with open(log_dir / "query_rewrite.log", 'a', encoding='utf-8') as f:
                    from datetime import datetime
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {log_msg}\n")
            except Exception as e:
                print(f"[KB] 查询改写失败，使用原查询: {e}")
        
        results = kb.search(rewritten_query, top_k=top_k)
        
        # 过滤低于阈值的结果
        filtered_results = []
        recalled_files = {}  # 统计每个文件被召回的次数
        
        for r in results:
            if r['score'] >= threshold:
                source_file = r['metadata'].get('source', 'unknown')
                recalled_files[source_file] = recalled_files.get(source_file, 0) + 1
                
                filtered_results.append({
                    "content": r['document'],
                    "score": round(r['score'], 4),
                    "file": source_file,
                    "title": r['metadata'].get('title', ''),
                    "chunk_id": r['metadata'].get('chunk_id', 0)
                })
        
        # 更新召回次数到 text.json
        if recalled_files:
            kb_data = load_kb_json(kb_type)
            for file_info in kb_data.get('files', []):
                filename = file_info['name']
                if filename in recalled_files:
                    file_info['recall'] = file_info.get('recall', 0) + recalled_files[filename]
            save_kb_json(kb_type, kb_data)
        
        response_data = {
            "success": True, 
            "results": filtered_results, 
            "total": len(filtered_results)
        }
        
        # 如果启用了改写，返回改写后的查询
        if use_rewrite and rewritten_query != query:
            response_data["rewritten_query"] = rewritten_query
        
        return jsonify(response_data)
    except Exception as e:
        print(f"[KB] 检索失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/kb/status', methods=['GET'])
def kb_status():
    """获取知识库状态"""
    kb_type = request.args.get('type', 'guide')
    kb_folder = KB_TYPE_MAP.get(kb_type, kb_type)
    kb_dir = KB_BASE_DIR / kb_folder
    index_dir = kb_dir / "index"
    index_file = index_dir / "index.pkl"
    data_dir = kb_dir / "data"
    
    # 从 text.json 读取文件数量
    kb_data = load_kb_json(kb_type)
    file_count = len(kb_data.get('files', []))
    
    status = {
        "kb_type": kb_type,
        "kb_available": KB_AVAILABLE,
        "index_exists": index_file.exists(),  # 检查索引文件是否存在
        "data_dir_exists": data_dir.exists(),
        "file_count": file_count,
        "loaded": kb_type in _kb_instances,
        "doc_count": 0
    }
    
    # 优先从索引文件读取文档数量
    if index_file.exists():
        try:
            # 尝试从缓存实例读取
            if kb_type in _kb_instances and _kb_instances[kb_type].vector_store:
                status["doc_count"] = _kb_instances[kb_type].vector_store.index.ntotal
            else:
                # 如果缓存中没有，尝试加载索引文件
                import pickle
                with open(index_file, 'rb') as f:
                    index_data = pickle.load(f)
                    if 'index' in index_data:
                        status["doc_count"] = index_data['index'].ntotal
        except Exception as e:
            print(f"[KB] 读取索引文件失败: {e}")
            # 如果读取失败，从 text.json 读取
            status["doc_count"] = kb_data.get('total_chunks', 0)
    else:
        # 索引文件不存在，清除缓存
        if kb_type in _kb_instances:
            del _kb_instances[kb_type]
            print(f"[KB] 索引文件不存在，已清除缓存: {kb_type}")
        status["doc_count"] = 0
    
    return jsonify(status)


@app.route('/api/kb/delete', methods=['POST'])
def kb_delete_file():
    """删除知识库文件"""
    data = request.get_json(force=True, silent=True) or {}
    kb_type = data.get('kb_type', 'guide')
    filename = data.get('filename', '')
    
    if not filename:
        return jsonify({"success": False, "error": "文件名不能为空"}), 400
    
    kb_folder = KB_TYPE_MAP.get(kb_type, kb_type)
    kb_dir = KB_BASE_DIR / kb_folder
    file_path = kb_dir / "data" / filename
    
    if file_path.exists():
        file_path.unlink()
        
        # 从 text.json 中移除该文件
        kb_data = load_kb_json(kb_type)
        kb_data['files'] = [f for f in kb_data.get('files', []) if f['name'] != filename]
        
        # 如果没有文件了，删除索引
        if not kb_data['files']:
            kb_data['index_built'] = False
            kb_data['total_chunks'] = 0
            
            # 删除索引文件
            index_dir = kb_dir / "index"
            if index_dir.exists():
                import shutil
                shutil.rmtree(index_dir)
                print(f"[KB] 已删除索引目录: {index_dir}")
        else:
            # 还有其他文件，需要重新构建索引
            kb_data['index_built'] = False
        
        save_kb_json(kb_type, kb_data)
        
        # 清除缓存的实例
        if kb_type in _kb_instances:
            del _kb_instances[kb_type]
            print(f"[KB] 已清除知识库缓存: {kb_type}")
        
        return jsonify({"success": True, "message": "文件已删除"})
    
    return jsonify({"success": False, "error": "文件不存在"}), 404


@app.route('/api/kb/clear_cache', methods=['POST'])
def kb_clear_cache():
    """清除知识库缓存"""
    data = request.get_json(force=True, silent=True) or {}
    kb_type = data.get('kb_type', 'all')
    
    if kb_type == 'all':
        # 清除所有缓存
        cleared = list(_kb_instances.keys())
        _kb_instances.clear()
        print(f"[KB] 已清除所有知识库缓存: {cleared}")
        return jsonify({"success": True, "message": f"已清除所有知识库缓存", "cleared": cleared})
    else:
        # 清除指定类型的缓存
        if kb_type in _kb_instances:
            del _kb_instances[kb_type]
            print(f"[KB] 已清除知识库缓存: {kb_type}")
            return jsonify({"success": True, "message": f"已清除 {kb_type} 知识库缓存"})
        else:
            return jsonify({"success": True, "message": f"{kb_type} 知识库未缓存"})


def preload_models(preload_vl: bool = False):
    """
    预加载模型，加速首次请求响应
    
    Args:
        preload_vl: 是否预加载本地多模态模型（占用较多显存）
    """
    print("\n" + "="*50)
    print("正在预加载模型...")
    print("="*50)
    
    # 1. 预加载知识库（包括向量化模型）
    if KB_AVAILABLE:
        print("\n[预加载] 知识库模块...")
        for kb_type in ['guide', 'diagnosis', 'safety']:
            try:
                kb = get_kb_instance(kb_type)
                if kb and kb.vector_store and kb.vector_store.index.ntotal > 0:
                    print(f"  ✓ {kb_type}: 已加载 {kb.vector_store.index.ntotal} 个文档块")
                else:
                    print(f"  - {kb_type}: 索引为空或未构建")
            except Exception as e:
                print(f"  ✗ {kb_type}: 加载失败 - {e}")
    else:
        print("\n[预加载] 知识库模块不可用")
    
    # 2. 预加载语音识别模型
    if asr_recognize:
        print("\n[预加载] 语音识别模型...")
        try:
            from models.ASR.asr_runner import preload_model
            preload_model()
            print("  ✓ ASR 模型加载成功")
        except ImportError:
            print("  - ASR 模型无预加载函数，将在首次使用时加载")
        except Exception as e:
            print(f"  ✗ ASR 模型加载失败: {e}")
    else:
        print("\n[预加载] 语音识别模块不可用")
    
    # 3. 预加载本地多模态模型（可选，占用较多显存）
    if preload_vl:
        print("\n[预加载] 本地多模态模型...")
        try:
            from models.LLM.local_LLM_VL import preload_model as preload_vl_model
            preload_vl_model()
            print("  ✓ 本地多模态模型加载成功")
        except ImportError:
            print("  - 本地多模态模型模块未安装")
        except Exception as e:
            print(f"  ✗ 本地多模态模型加载失败: {e}")
    else:
        print("\n[预加载] 本地多模态模型: 跳过（首次使用时加载）")
    
    print("\n" + "="*50)
    print("预加载完成！")
    print("="*50 + "\n")


# ==================== IDE 路由 ====================

@app.route('/ide')
def ide_page():
    """IDE 主页面"""
    return render_template('templates/ide.html')


@app.route('/api/ide/run', methods=['POST'])
def ide_run_code():
    """运行代码"""
    try:
        from models.IDE import CodeExecutor, handle_execution_error, format_error_message
        
        data = request.get_json(force=True, silent=True) or {}
        code = data.get('code', '').strip()
        language = data.get('language', 'python')
        session_id = data.get('session_id')
        
        if not code:
            return jsonify({'error': '代码不能为空'}), 400
        
        # 执行代码
        executor = CodeExecutor()
        result = executor.execute(code, language)
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        print(f"IDE 运行代码错误: {e}")
        return jsonify({'error': f'系统错误: {str(e)}'}), 500


@app.route('/api/ide/debug', methods=['POST'])
def ide_debug_code():
    """AI 代码调试接口 - 将代码和错误信息发送给大模型进行分析"""
    try:
        from models.IDE import CodeExecutor
        
        data = request.get_json(force=True, silent=True) or {}
        code = data.get('code', '').strip()
        language = data.get('language', 'python')
        error_info = data.get('error_info', {})  # 执行错误信息
        user_question = data.get('user_question', '')  # 用户的问题
        session_id = data.get('session_id')
        
        # 获取模型配置
        model = data.get('model')
        provider_id = data.get('provider_id')
        api_key = data.get('api_key', '')
        base_url = data.get('base_url', '')
        
        if not code:
            return jsonify({'error': '代码不能为空'}), 400
        
        # 如果没有提供错误信息且没有用户问题，先执行代码获取错误
        if not error_info and not user_question:
            executor = CodeExecutor()
            result = executor.execute(code, language)
            
            # 如果执行成功，返回成功信息
            if result.success:
                return jsonify({
                    'success': True,
                    'message': '代码执行成功，无需调试',
                    'result': result.to_dict()
                })
            
            # 提取错误信息
            error_info = {
                'stderr': result.stderr,
                'exit_code': result.exit_code,
                'error': result.error
            }
        
        # 构建调试提示词 - 激活代码调试场景
        if PROMPT_ENGINE_AVAILABLE and get_prompt_engine:
            try:
                engine = get_prompt_engine()
                system_prompt = engine.generate_prompt(ScenarioType.CODE_DEBUG)
            except Exception as e:
                print(f"获取代码调试提示词失败: {e}")
                system_prompt = "你是一位资深的代码审查专家，擅长快速定位并修复代码错误。"
        else:
            system_prompt = "你是一位资深的代码审查专家，擅长快速定位并修复代码错误。"
        
        # 构建用户消息
        if user_question:
            # 用户有具体问题
            user_message = f"""## 用户问题
{user_question}

## 当前代码
**编程语言**: {language}

```{language}
{code}
```

请根据用户的问题分析代码并给出详细解答。
"""
        else:
            # 自动调试模式
            user_message = f"""请帮我分析并修复以下代码的错误：

## 代码信息
**编程语言**: {language}

## 原始代码
```{language}
{code}
```

## 错误信息
**退出码**: {error_info.get('exit_code', 'N/A')}

**错误输出**:
```
{error_info.get('stderr', '未知错误')}
```

请按照以下格式输出：
1. 错误诊断（错误位置、错误类型、错误原因）
2. 修复方案（修复后代码、Diff 格式、修复说明）
3. 测试用例（验证修复效果）
"""
        
        # 调用大模型进行分析
        if call_model_stream is None:
            return jsonify({'error': '后端未正确加载 llm_runner'}), 500
        
        def generate():
            full = []
            try:
                for chunk in call_model_stream(
                    message=user_message,
                    provider_id=provider_id,
                    model_id=model,
                    system_prompt=system_prompt,
                    api_key=api_key or None,
                    base_url=base_url or None,
                ):
                    if chunk:
                        full.append(chunk)
                        yield chunk
                
                # 保存调试历史
                bot_resp = "".join(full)
                meta = {
                    "type": "code_debug",
                    "model": model,
                    "provider": provider_id,
                    "language": language,
                    "scenario": "code_debug"
                }
                if user_question:
                    append_history("user", f"[代码调试] {user_question}\n```{language}\n{code}\n```", meta, session_id=session_id)
                else:
                    append_history("user", f"[代码调试] {language} 代码\n```{language}\n{code}\n```", meta, session_id=session_id)
                append_history("assistant", bot_resp, meta, session_id=session_id)
                
            except Exception as e:
                print(f"代码调试失败: {e}")
                yield f"[ERROR] 调试失败: {e}"
        
        return Response(stream_with_context(generate()), mimetype='text/plain')
        
    except Exception as e:
        print(f"IDE 代码调试错误: {e}")
        return jsonify({'error': f'系统错误: {str(e)}'}), 500


@app.route('/api/ide/session', methods=['POST'])
def ide_create_session():
    """创建 IDE 会话"""
    try:
        from models.IDE import IDESessionManager
        
        sessions_dir = DATA_DIR / "ide_sessions"
        session_manager = IDESessionManager(str(sessions_dir))
        
        result = session_manager.create_session()
        return jsonify(result)
        
    except Exception as e:
        print(f"创建会话错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ide/languages', methods=['GET'])
def ide_get_languages():
    """获取支持的语言列表"""
    try:
        from models.IDE import CodeExecutor
        
        executor = CodeExecutor()
        languages = executor.get_supported_languages()
        
        return jsonify({'languages': languages})
    except Exception as e:
        print(f"获取语言列表错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ide/files', methods=['GET'])
def ide_list_files():
    """列出会话中的所有文件"""
    try:
        from models.IDE import FileManager
        
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'error': '缺少 session_id'}), 400
        
        # 获取会话目录
        session_dir = DATA_DIR / "ide_sessions" / session_id
        file_manager = FileManager(str(session_dir))
        
        result = file_manager.list_files()
        return jsonify(result)
        
    except Exception as e:
        print(f"列出文件错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ide/files', methods=['POST'])
def ide_create_file():
    """创建新文件"""
    try:
        from models.IDE import FileManager
        
        data = request.get_json(force=True, silent=True) or {}
        session_id = data.get('session_id')
        filename = data.get('filename', '').strip()
        content = data.get('content', '')
        
        if not session_id:
            return jsonify({'error': '缺少 session_id'}), 400
        if not filename:
            return jsonify({'error': '缺少文件名'}), 400
        
        # 获取会话目录
        session_dir = DATA_DIR / "ide_sessions" / session_id
        file_manager = FileManager(str(session_dir))
        
        result = file_manager.create_file(filename, content)
        return jsonify(result)
        
    except Exception as e:
        print(f"创建文件错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ide/files/<filename>', methods=['GET'])
def ide_read_file(filename):
    """读取文件内容"""
    try:
        from models.IDE import FileManager
        
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'error': '缺少 session_id'}), 400
        
        # 获取会话目录
        session_dir = DATA_DIR / "ide_sessions" / session_id
        file_manager = FileManager(str(session_dir))
        
        result = file_manager.read_file(filename)
        return jsonify(result)
        
    except Exception as e:
        print(f"读取文件错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ide/files/<filename>', methods=['PUT'])
def ide_update_file(filename):
    """更新文件内容"""
    try:
        from models.IDE import FileManager
        
        data = request.get_json(force=True, silent=True) or {}
        session_id = data.get('session_id')
        content = data.get('content', '')
        
        if not session_id:
            return jsonify({'error': '缺少 session_id'}), 400
        
        # 获取会话目录
        session_dir = DATA_DIR / "ide_sessions" / session_id
        file_manager = FileManager(str(session_dir))
        
        result = file_manager.update_file(filename, content)
        return jsonify(result)
        
    except Exception as e:
        print(f"更新文件错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ide/files/<filename>', methods=['DELETE'])
def ide_delete_file(filename):
    """删除文件"""
    try:
        from models.IDE import FileManager
        
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'error': '缺少 session_id'}), 400
        
        # 获取会话目录
        session_dir = DATA_DIR / "ide_sessions" / session_id
        file_manager = FileManager(str(session_dir))
        
        result = file_manager.delete_file(filename)
        return jsonify(result)
        
    except Exception as e:
        print(f"删除文件错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ide/files/rename', methods=['POST'])
def ide_rename_file():
    """重命名文件"""
    try:
        from models.IDE import FileManager
        
        data = request.get_json(force=True, silent=True) or {}
        session_id = data.get('session_id')
        old_filename = data.get('old_filename', '').strip()
        new_filename = data.get('new_filename', '').strip()
        
        if not session_id:
            return jsonify({'error': '缺少 session_id'}), 400
        if not old_filename or not new_filename:
            return jsonify({'error': '缺少文件名'}), 400
        
        # 获取会话目录
        session_dir = DATA_DIR / "ide_sessions" / session_id
        file_manager = FileManager(str(session_dir))
        
        result = file_manager.rename_file(old_filename, new_filename)
        return jsonify(result)
        
    except Exception as e:
        print(f"重命名文件错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ide/session/<session_id>', methods=['GET'])
def ide_load_session(session_id):
    """加载会话状态"""
    try:
        from models.IDE import IDESessionManager
        
        sessions_dir = DATA_DIR / "ide_sessions"
        session_manager = IDESessionManager(str(sessions_dir))
        
        result = session_manager.load_session(session_id)
        return jsonify(result)
        
    except Exception as e:
        print(f"加载会话错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ide/session/<session_id>', methods=['PUT'])
def ide_save_session(session_id):
    """保存会话状态"""
    try:
        from models.IDE import IDESessionManager
        
        data = request.get_json(force=True, silent=True) or {}
        editor_state = data.get('editor_state', {})
        
        sessions_dir = DATA_DIR / "ide_sessions"
        session_manager = IDESessionManager(str(sessions_dir))
        
        result = session_manager.save_session(session_id, editor_state)
        return jsonify(result)
        
    except Exception as e:
        print(f"保存会话错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ide/session/<session_id>', methods=['DELETE'])
def ide_delete_session(session_id):
    """删除会话"""
    try:
        from models.IDE import IDESessionManager
        
        sessions_dir = DATA_DIR / "ide_sessions"
        session_manager = IDESessionManager(str(sessions_dir))
        
        result = session_manager.delete_session(session_id)
        return jsonify(result)
        
    except Exception as e:
        print(f"删除会话错误: {e}")
        return jsonify({'error': str(e)}), 500


# 环境变量控制是否预加载多模态模型
PRELOAD_VL = os.environ.get("PRELOAD_VL", "false").lower() in ("true", "1", "yes")


if __name__ == '__main__':
    # 初始化 Docker 和 Piston
    try:
        initialize_docker_and_piston()
    except Exception as e:
        print(f"⚠️  初始化 Docker/Piston 时出错: {e}")
        print("   应用将继续启动，但代码执行功能可能不可用")
    
    # 支持通过环境变量调整监听地址/端口，避免端口被占用时启动失败
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "5000"))

    # 预加载模型（多模态模型可选）
    preload_models(preload_vl=PRELOAD_VL)

    print("\n" + "="*60)
    print("🎯 启动 Flask 服务器")
    print("="*60)
    print(f"请在浏览器访问 http://{host}:{port}")
    print("="*60 + "\n")
    # Windows 上 debug 模式建议关闭 reloader，避免重复绑定端口
    app.run(debug=True, host=host, port=port, use_reloader=False)
