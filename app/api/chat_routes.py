"""对话相关路由：普通/流式/带文件问答、模型配置、会话历史、联网搜索。"""
import uuid
from pathlib import Path

from flask import Blueprint, Response, jsonify, request, stream_with_context

from .. import runtime
from ..config import UPLOAD_DIR, ensure_dirs, get_system_prompt, load_llm_config
from ..observability import get_logger
from ..security.validation import safe_filename
from ..services.history import append_history, get_session_file, read_history

bp = Blueprint('chat_routes', __name__)
logger = get_logger()

# 携带知识库参考资料时，强制模型标注依据来源，抑制无依据回答
CITATION_INSTRUCTION = """

【引用要求】本次提问附带了知识库参考资料。回答时必须遵守：
1. 优先依据参考资料回答；资料未覆盖的内容如需补充，必须明确标注"（以下为通用建议，非知识库内容）"；
2. 回答末尾用如下格式列出依据来源：
   > 来源：《文档名》
   > 章节：命中的章节标题（若有）
   > 依据：所引用的关键原文（摘录）
3. 如果参考资料与问题无关或不足以回答，直接说明"知识库中未找到相关依据"，不要编造。"""


@bp.route('/api/chat', methods=['POST'])
def chat():
    """处理前端发来的聊天请求"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        user_message = (data.get('message') or '').strip()

        model = data.get('model', None)
        system_prompt = data.get('system_prompt', '')
        api_key = data.get('api_key', '')
        base_url = data.get('base_url', '')
        provider_id = data.get('provider_id', None)
        session_id = data.get('session_id', None)

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        logger.info(f"[chat] model={model} provider={provider_id} session={session_id}")

        if runtime.call_model is None:
            return jsonify({'error': '后端未正确加载 llm_runner，请检查导入'}), 500

        try:
            bot_response = runtime.call_model(
                message=user_message,
                provider_id=provider_id,
                model_id=model,
                system_prompt=system_prompt,
                api_key=api_key or None,
                base_url=base_url or None,
            )
        except Exception as e:
            logger.error(f"[chat] LLM 调用失败: {e}")
            return jsonify({'error': f'LLM 调用失败: {e}'}), 500

        meta = {"type": "chat", "model": model, "provider": provider_id}
        append_history("user", user_message, meta, session_id=session_id)
        append_history("assistant", bot_response, meta, session_id=session_id)

        return jsonify({'response': bot_response})

    except Exception as e:
        logger.error(f"[chat] Error: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/chat_stream', methods=['POST'])
def chat_stream():
    """流式输出接口，逐段返回文本。"""
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
        kb_sources = data.get('kb_sources', [])
        enable_thinking = data.get('enable_thinking', False)
        enable_web_search = data.get('enable_web_search', False)
        web_search_query = data.get('web_search_query', '')

        logger.info(f"[chat_stream] model={model} provider={provider_id} "
                    f"thinking={enable_thinking} web_search={enable_web_search}")

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        if runtime.call_model_stream is None:
            return jsonify({'error': '后端未正确加载 llm_runner，请检查导入'}), 500

        # 带知识库参考资料的请求：追加引用来源约束
        if kb_sources:
            system_prompt = (system_prompt or '') + CITATION_INSTRUCTION

        enhanced_message = user_message
        detected_scenario = None

        # 联网搜索功能
        web_search_results = []
        if enable_web_search and runtime.WEB_SEARCH_AVAILABLE:
            try:
                search_query = web_search_query if web_search_query else user_message
                logger.info(f"[chat_stream] 联网搜索: {search_query}")

                search_result = runtime.search_and_format(search_query, max_results=5)

                if search_result["success"]:
                    web_search_context = search_result["formatted_text"]
                    web_search_results = search_result["raw_data"]
                    logger.info(f"[chat_stream] 联网搜索成功，{len(web_search_results)} 条结果")
                    enhanced_message = (f"{web_search_context}\n\n用户问题: {user_message}\n\n"
                                        f"请根据以上搜索到的信息回答用户的问题。")
                else:
                    logger.warning(f"[chat_stream] 联网搜索失败: {search_result.get('error', '未知错误')}")
            except Exception as e:
                logger.error(f"[chat_stream] 联网搜索异常: {e}")

        def generate():
            full = []
            try:
                for chunk in runtime.call_model_stream(
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
                logger.info(f"[chat_stream] 输出完成，长度: {len(bot_resp)}")
                meta = {"type": "chat", "model": model, "provider": provider_id}
                if detected_scenario:
                    meta["scenario"] = detected_scenario
                if enable_web_search and web_search_results:
                    meta["web_search"] = True
                    meta["search_query"] = web_search_query or user_message
                append_history("user", original_message, meta, session_id=session_id)
                bot_meta = {"type": "chat", "model": model, "provider": provider_id}
                if kb_sources:
                    bot_meta["kb_sources"] = kb_sources
                if detected_scenario:
                    bot_meta["scenario"] = detected_scenario
                if enable_web_search and web_search_results:
                    bot_meta["web_search_results"] = web_search_results
                append_history("assistant", bot_resp, bot_meta, session_id=session_id)
            except Exception as e:
                logger.error(f"[chat_stream] 流式调用失败: {e}")
                yield f"[ERROR]{e}"

        return Response(stream_with_context(generate()), mimetype='text/plain')

    except Exception as e:
        logger.error(f"[chat_stream] Error: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/chat_with_file', methods=['POST'])
def chat_with_file():
    """带文件的聊天接口（流式），支持文本和图片多模态"""
    if runtime.call_model_stream is None:
        return jsonify({'error': '后端未正确加载 llm_runner'}), 500

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
        safe_name = safe_filename(original_filename)

        if not safe_name or not Path(safe_name).suffix:
            safe_name = f"file_{uuid.uuid4().hex}{ext}"

        saved_filename = safe_name

        ensure_dirs()
        save_path = UPLOAD_DIR / safe_name
        file.save(save_path)

        if ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}:
            image_file_path = str(save_path)

        logger.info(f"[chat_with_file] 文件已保存: {save_path}")

        if runtime.parse_for_chat:
            result = runtime.parse_for_chat(str(save_path), message)
            if result['success']:
                messages_list = result.get('messages', [])
                has_image = any(
                    msg.get('type') == 'image_url'
                    for msg in messages_list
                )
                if has_image:
                    is_multimodal = True
                    final_message = messages_list
                elif messages_list and messages_list[0].get('type') == 'text':
                    final_message = messages_list[0].get('text', '')
            else:
                logger.warning(f"[chat_with_file] 解析失败: {result.get('error')}")
                return jsonify({'error': f"文件解析失败: {result.get('error')}"}), 400
        else:
            return jsonify({'error': '文件解析服务未加载'}), 500

    if not final_message:
        return jsonify({'error': '无法解析文件内容'}), 400

    def generate():
        full = []
        try:
            # 本地多模态模型使用原始文本 + image_path；远程多模态模型使用 parse_for_chat 返回的消息列表
            request_message = message if is_local_vl_provider else final_message
            for chunk in runtime.call_model_stream(
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
            logger.error(f"[chat_with_file] 流式调用失败: {e}")
            yield f"[ERROR]{e}"

    return Response(stream_with_context(generate()), mimetype='text/plain')


@bp.route('/api/llm_config', methods=['GET'])
def api_llm_config():
    """返回 models_config.json 内容，供前端模型选择使用。"""
    return jsonify(load_llm_config())


@bp.route('/api/history', methods=['GET'])
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


@bp.route('/api/session/new', methods=['POST'])
def new_session():
    """创建新会话，返回新的 session_id"""
    session_id = str(uuid.uuid4())
    return jsonify({"session_id": session_id})


@bp.route('/api/session/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """删除指定会话"""
    session_file = get_session_file(session_id)
    if session_file.exists():
        session_file.unlink()
        return jsonify({"success": True, "message": "会话已删除"})
    return jsonify({"success": False, "message": "会话不存在"}), 404


@bp.route('/api/web_search', methods=['POST'])
def api_web_search():
    """联网搜索 API"""
    if not runtime.WEB_SEARCH_AVAILABLE:
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

        result = runtime.search_and_format(query, max_results=max_results)
        return jsonify(result)

    except Exception as e:
        logger.error(f"[web_search] 联网搜索失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/web_search/status', methods=['GET'])
def api_web_search_status():
    """检查联网搜索功能状态"""
    import os
    return jsonify({
        'available': runtime.WEB_SEARCH_AVAILABLE,
        'api_key_configured': bool(os.getenv('METASO_API_KEY'))
    })
