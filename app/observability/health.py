"""健康检查接口：存活/就绪探针与能力清单。"""
from flask import Blueprint, jsonify

from .. import runtime
from ..retrieval import reranker
from ..security import auth
from ..services.sandbox import check_docker_running, check_piston_running

bp = Blueprint('health', __name__)


@bp.route('/health/live', methods=['GET'])
def health_live():
    """存活探针：进程在跑就返回 200。"""
    return jsonify({"status": "ok"})


@bp.route('/health/ready', methods=['GET'])
def health_ready():
    """就绪探针：核心问答链路（LLM 调用）可用才算就绪。"""
    ready = runtime.call_model_stream is not None
    return jsonify({
        "status": "ready" if ready else "not_ready",
        "llm_runner": runtime.call_model_stream is not None,
    }), (200 if ready else 503)


@bp.route('/health/capabilities', methods=['GET'])
def health_capabilities():
    """能力清单：明确显示各子系统是否可用，避免"页面能开但核心功能失效"。"""
    docker_ok = False
    piston_ok = False
    try:
        docker_ok = check_docker_running()
        if docker_ok:
            piston_ok = check_piston_running()
    except Exception:
        pass

    return jsonify({
        "llm": runtime.call_model_stream is not None,
        "rag": runtime.KB_AVAILABLE,
        "prompt_engine": runtime.PROMPT_ENGINE_AVAILABLE,
        "asr": runtime.asr_recognize is not None,
        "ocr": runtime.ocr_recognize is not None,
        "tts": runtime.tts_synthesize is not None,
        "web_search": runtime.WEB_SEARCH_AVAILABLE,
        "docker": docker_ok,
        "code_sandbox": piston_ok,
        "reranker": reranker.is_available(),
        "admin_token_configured": bool(auth.ADMIN_TOKEN),
    })
