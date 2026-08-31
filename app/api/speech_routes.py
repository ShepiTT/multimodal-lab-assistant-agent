"""语音与图像识别路由：ASR、TTS、OCR。"""
import base64
import json
import uuid
from pathlib import Path

import requests
from flask import Blueprint, jsonify, request

from .. import runtime
from ..config import UPLOAD_DIR, VOICE_DATA_DIR, ensure_dirs
from ..observability import get_logger
from ..security.validation import safe_filename
from ..services.history import append_history

bp = Blueprint('speech_routes', __name__)
logger = get_logger()


# ---- 百度 ASR 直连回退（未加载统一 ASR runner 时使用）----

def _baidu_get_token() -> str:
    cfg = runtime.get_asr_model_config() if runtime.get_asr_model_config else {}
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


def _baidu_asr(audio_bytes: bytes, fmt: str = "wav", rate: int = 16000, channel: int = 1) -> str:
    token = _baidu_get_token()
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


@bp.route('/api/asr', methods=['POST'])
def asr():
    """语音识别接口"""
    if 'file' not in request.files:
        return jsonify({"error": "缺少音频文件"}), 400

    file = request.files['file']
    provider_id = request.form.get('provider_id')  # 可选，指定 ASR provider

    original_filename = file.filename or ""
    original_ext = Path(original_filename).suffix.lower() or '.webm'

    filename = safe_filename(original_filename) or f"audio_{uuid.uuid4().hex}{original_ext}"
    ensure_dirs()
    save_path = VOICE_DATA_DIR / filename
    file.save(save_path)

    fmt = (filename.rsplit('.', 1)[-1] if '.' in filename else 'wav').lower()
    actual_path = save_path  # 实际用于识别的文件路径

    logger.info(f"[ASR] 收到音频文件: {filename}, 格式: {fmt}, provider: {provider_id}")

    # 对于非 wav/pcm 格式，尝试转换为 wav（百度 ASR 只支持 wav/pcm）
    need_convert = fmt not in ('wav', 'pcm')

    if need_convert and runtime.convert_to_wav:
        logger.info(f"[ASR] 转换音频格式: {fmt} -> wav")
        wav_path = str(save_path.with_suffix('.wav'))
        success, result = runtime.convert_to_wav(str(save_path), wav_path)
        if success:
            actual_path = Path(result)
            fmt = 'wav'
        else:
            logger.warning(f"[ASR] 转换失败: {result}，尝试用原格式继续")
    elif need_convert:
        logger.warning("[ASR] 需要转换但 convert_to_wav 不可用，请安装 ffmpeg")

    try:
        if runtime.asr_recognize:
            transcript = runtime.asr_recognize(str(actual_path), provider_id=provider_id, format=fmt)
        else:
            # 回退到旧的百度 ASR（需要 wav 格式）
            if fmt != 'wav':
                return jsonify({"error": f"百度 ASR 不支持 {fmt} 格式，请安装 ffmpeg 进行格式转换"}), 400

            audio_bytes = actual_path.read_bytes()
            transcript = _baidu_asr(audio_bytes, fmt=fmt)
    except Exception as e:
        logger.error(f"[ASR] 失败: {e}")
        return jsonify({"error": f"ASR 失败: {e}"}), 500

    meta = {"type": "asr", "filename": filename, "file_url": f"/voice_data/{filename}"}
    append_history("assistant", f"语音转写：{transcript}", meta)

    return jsonify({
        "text": transcript,
        "file_url": meta["file_url"],
        "meta": meta
    })


@bp.route('/api/tts', methods=['POST'])
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
        if runtime.tts_synthesize:
            runtime.tts_synthesize(
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
        logger.error(f"[TTS] 失败: {e}")
        return jsonify({"error": f"TTS 失败: {e}"}), 500

    audio_url = f"/uploads/{audio_name}"
    meta = {"type": "tts", "audio_url": audio_url}
    append_history("assistant", f"已生成语音：{text[:60]}", meta)

    return jsonify({"audio_url": audio_url, "meta": meta})


@bp.route('/api/ocr', methods=['POST'])
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
        if runtime.ocr_recognize:
            text = runtime.ocr_recognize(str(save_path), provider_id=provider_id)
        else:
            return jsonify({"error": "OCR 服务未配置"}), 500
    except Exception as e:
        logger.error(f"[OCR] 失败: {e}")
        return jsonify({"error": f"OCR 失败: {e}"}), 500

    return jsonify({
        "text": text,
        "file_url": f"/uploads/{filename}"
    })
