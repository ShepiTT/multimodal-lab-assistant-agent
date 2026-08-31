"""IDE 路由：代码执行、AI 调试、文件与会话管理。

session_id 一律经过 get_ide_session_dir 校验，防止目录穿越。
"""
from flask import Blueprint, Response, jsonify, request, stream_with_context

from .. import runtime
from ..config import DATA_DIR
from ..observability import get_logger
from ..security.validation import get_ide_session_dir
from ..services.history import append_history

bp = Blueprint('ide_routes', __name__)
logger = get_logger()


@bp.route('/api/ide/run', methods=['POST'])
def ide_run_code():
    """运行代码"""
    try:
        from models.IDE import CodeExecutor

        data = request.get_json(force=True, silent=True) or {}
        code = data.get('code', '').strip()
        language = data.get('language', 'python')

        if not code:
            return jsonify({'error': '代码不能为空'}), 400

        executor = CodeExecutor()
        result = executor.execute(code, language)

        return jsonify(result.to_dict())

    except Exception as e:
        logger.error(f"[IDE] 运行代码错误: {e}")
        return jsonify({'error': f'系统错误: {str(e)}'}), 500


@bp.route('/api/ide/debug', methods=['POST'])
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

            if result.success:
                return jsonify({
                    'success': True,
                    'message': '代码执行成功，无需调试',
                    'result': result.to_dict()
                })

            error_info = {
                'stderr': result.stderr,
                'exit_code': result.exit_code,
                'error': result.error
            }

        # 构建调试提示词 - 激活代码调试场景
        if runtime.PROMPT_ENGINE_AVAILABLE and runtime.get_prompt_engine:
            try:
                engine = runtime.get_prompt_engine()
                system_prompt = engine.generate_prompt(runtime.ScenarioType.CODE_DEBUG)
            except Exception as e:
                logger.warning(f"[IDE] 获取代码调试提示词失败: {e}")
                system_prompt = "你是一位资深的代码审查专家，擅长快速定位并修复代码错误。"
        else:
            system_prompt = "你是一位资深的代码审查专家，擅长快速定位并修复代码错误。"

        # 构建用户消息
        if user_question:
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

        if runtime.call_model_stream is None:
            return jsonify({'error': '后端未正确加载 llm_runner'}), 500

        def generate():
            full = []
            try:
                for chunk in runtime.call_model_stream(
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

                bot_resp = "".join(full)
                meta = {
                    "type": "code_debug",
                    "model": model,
                    "provider": provider_id,
                    "language": language,
                    "scenario": "code_debug"
                }
                if user_question:
                    append_history("user", f"[代码调试] {user_question}\n```{language}\n{code}\n```",
                                   meta, session_id=session_id)
                else:
                    append_history("user", f"[代码调试] {language} 代码\n```{language}\n{code}\n```",
                                   meta, session_id=session_id)
                append_history("assistant", bot_resp, meta, session_id=session_id)

            except Exception as e:
                logger.error(f"[IDE] 代码调试失败: {e}")
                yield f"[ERROR] 调试失败: {e}"

        return Response(stream_with_context(generate()), mimetype='text/plain')

    except Exception as e:
        logger.error(f"[IDE] 代码调试错误: {e}")
        return jsonify({'error': f'系统错误: {str(e)}'}), 500


@bp.route('/api/ide/session', methods=['POST'])
def ide_create_session():
    """创建 IDE 会话"""
    try:
        from models.IDE import IDESessionManager

        sessions_dir = DATA_DIR / "ide_sessions"
        session_manager = IDESessionManager(str(sessions_dir))

        result = session_manager.create_session()
        return jsonify(result)

    except Exception as e:
        logger.error(f"[IDE] 创建会话错误: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/ide/languages', methods=['GET'])
def ide_get_languages():
    """获取支持的语言列表"""
    try:
        from models.IDE import CodeExecutor

        executor = CodeExecutor()
        languages = executor.get_supported_languages()

        return jsonify({'languages': languages})
    except Exception as e:
        logger.error(f"[IDE] 获取语言列表错误: {e}")
        return jsonify({'error': str(e)}), 500


def _session_file_manager(session_id):
    """校验 session_id 并返回 FileManager；非法 id 抛 ValueError。"""
    from models.IDE import FileManager
    session_dir = get_ide_session_dir(session_id)
    return FileManager(str(session_dir))


@bp.route('/api/ide/files', methods=['GET'])
def ide_list_files():
    """列出会话中的所有文件"""
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'error': '缺少 session_id'}), 400

        try:
            file_manager = _session_file_manager(session_id)
        except ValueError:
            return jsonify({'error': '非法的 session_id'}), 400

        return jsonify(file_manager.list_files())

    except Exception as e:
        logger.error(f"[IDE] 列出文件错误: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/ide/files', methods=['POST'])
def ide_create_file():
    """创建新文件"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        session_id = data.get('session_id')
        filename = data.get('filename', '').strip()
        content = data.get('content', '')

        if not session_id:
            return jsonify({'error': '缺少 session_id'}), 400
        if not filename:
            return jsonify({'error': '缺少文件名'}), 400

        try:
            file_manager = _session_file_manager(session_id)
        except ValueError:
            return jsonify({'error': '非法的 session_id'}), 400

        return jsonify(file_manager.create_file(filename, content))

    except Exception as e:
        logger.error(f"[IDE] 创建文件错误: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/ide/files/<filename>', methods=['GET'])
def ide_read_file(filename):
    """读取文件内容"""
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'error': '缺少 session_id'}), 400

        try:
            file_manager = _session_file_manager(session_id)
        except ValueError:
            return jsonify({'error': '非法的 session_id'}), 400

        return jsonify(file_manager.read_file(filename))

    except Exception as e:
        logger.error(f"[IDE] 读取文件错误: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/ide/files/<filename>', methods=['PUT'])
def ide_update_file(filename):
    """更新文件内容"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        session_id = data.get('session_id')
        content = data.get('content', '')

        if not session_id:
            return jsonify({'error': '缺少 session_id'}), 400

        try:
            file_manager = _session_file_manager(session_id)
        except ValueError:
            return jsonify({'error': '非法的 session_id'}), 400

        return jsonify(file_manager.update_file(filename, content))

    except Exception as e:
        logger.error(f"[IDE] 更新文件错误: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/ide/files/<filename>', methods=['DELETE'])
def ide_delete_file(filename):
    """删除文件"""
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'error': '缺少 session_id'}), 400

        try:
            file_manager = _session_file_manager(session_id)
        except ValueError:
            return jsonify({'error': '非法的 session_id'}), 400

        return jsonify(file_manager.delete_file(filename))

    except Exception as e:
        logger.error(f"[IDE] 删除文件错误: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/ide/files/rename', methods=['POST'])
def ide_rename_file():
    """重命名文件"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        session_id = data.get('session_id')
        old_filename = data.get('old_filename', '').strip()
        new_filename = data.get('new_filename', '').strip()

        if not session_id:
            return jsonify({'error': '缺少 session_id'}), 400
        if not old_filename or not new_filename:
            return jsonify({'error': '缺少文件名'}), 400

        try:
            file_manager = _session_file_manager(session_id)
        except ValueError:
            return jsonify({'error': '非法的 session_id'}), 400

        return jsonify(file_manager.rename_file(old_filename, new_filename))

    except Exception as e:
        logger.error(f"[IDE] 重命名文件错误: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/ide/session/<session_id>', methods=['GET'])
def ide_load_session(session_id):
    """获取指定 IDE 会话信息"""
    try:
        from models.IDE import IDESessionManager

        sessions_dir = DATA_DIR / "ide_sessions"
        session_manager = IDESessionManager(str(sessions_dir))

        result = session_manager.load_session(session_id)
        return jsonify(result)

    except ValueError:
        return jsonify({'error': '非法的 session_id'}), 400
    except Exception as e:
        logger.error(f"[IDE] 加载会话错误: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/ide/session/<session_id>', methods=['PUT'])
def ide_save_session(session_id):
    """更新指定 IDE 会话状态"""
    try:
        from models.IDE import IDESessionManager

        data = request.get_json(force=True, silent=True) or {}
        editor_state = data.get('editor_state', {})

        sessions_dir = DATA_DIR / "ide_sessions"
        session_manager = IDESessionManager(str(sessions_dir))

        result = session_manager.save_session(session_id, editor_state)
        return jsonify(result)

    except ValueError:
        return jsonify({'error': '非法的 session_id'}), 400
    except Exception as e:
        logger.error(f"[IDE] 保存会话错误: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/ide/session/<session_id>', methods=['DELETE'])
def ide_delete_session(session_id):
    """删除指定 IDE 会话"""
    try:
        from models.IDE import IDESessionManager

        sessions_dir = DATA_DIR / "ide_sessions"
        session_manager = IDESessionManager(str(sessions_dir))

        result = session_manager.delete_session(session_id)
        return jsonify(result)

    except ValueError:
        return jsonify({'error': '非法的 session_id'}), 400
    except Exception as e:
        logger.error(f"[IDE] 删除会话错误: {e}")
        return jsonify({'error': str(e)}), 500
