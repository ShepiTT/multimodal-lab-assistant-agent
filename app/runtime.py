"""可选组件的受保护导入。

所有模型/服务模块都可能因缺少依赖而不可用，导入失败时置 None 并打印警告，
调用方通过判空实现优雅降级。/health/capabilities 根据这些标志报告能力状态。
"""
import sys

from .config import BASE_DIR

# 项目根目录加入 sys.path，保证 models/、knowledge_base/ 等顶层包可导入
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from models.LLM.llm_runner import call_model, call_model_stream  # 统一模型调用
except Exception as e:
    call_model = None
    call_model_stream = None
    print(f"[warn] 未能导入 models.LLM.llm_runner: {e}")

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
    validate_file = None
    ALL_EXTENSIONS = None
    SIZE_LIMITS = None
    print(f"[warn] 未能导入 parsing_service: {e}")

try:
    from knowledge_base.fault_diagnosis.vector_store import FaultDiagnosisKnowledgeBase
    KB_AVAILABLE = True
except Exception as e:
    FaultDiagnosisKnowledgeBase = None
    KB_AVAILABLE = False
    print(f"[warn] 未能导入知识库模块: {e}")

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

try:
    from web_search.search_api import search_and_format, search_web, format_search_results
    WEB_SEARCH_AVAILABLE = True
except Exception as e:
    search_and_format = None
    search_web = None
    format_search_results = None
    WEB_SEARCH_AVAILABLE = False
    print(f"[warn] 未能导入 web_search.search_api: {e}")
