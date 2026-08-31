"""Agent 路由：工具调用问答与故障诊断状态机。"""
from flask import Blueprint, jsonify, request

from ..agents.diagnosis import DiagnosisSession, start_session
from ..agents.loop import run_agent
from ..agents.tools import list_tools
from ..observability import get_logger

bp = Blueprint('agent_routes', __name__)
logger = get_logger()


@bp.route('/api/agent/tools', methods=['GET'])
def agent_list_tools():
    """列出 Agent 可用的工具。"""
    return jsonify({"tools": list_tools()})


@bp.route('/api/agent/chat', methods=['POST'])
def agent_chat():
    """工具调用 Agent 问答（非流式）。

    返回 {'answer', 'tool_trace', 'iterations'}；tool_trace 记录每次
    工具调用的名称、参数与结果，前端可用于展示执行过程。
    """
    data = request.get_json(force=True, silent=True) or {}
    message = (data.get('message') or '').strip()
    if not message:
        return jsonify({'error': 'No message provided'}), 400

    try:
        result = run_agent(
            message=message,
            provider_id=data.get('provider_id'),
            model_id=data.get('model'),
            system_prompt=data.get('system_prompt', ''),
            api_key=data.get('api_key') or None,
            base_url=data.get('base_url') or None,
        )
        return jsonify({'success': True, **result})
    except Exception as e:
        logger.error(f"[Agent] 运行失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/diagnosis/start', methods=['POST'])
def diagnosis_start():
    """创建故障诊断会话。"""
    session = start_session()
    return jsonify({
        'success': True,
        'session_id': session.session_id,
        'state': session.state,
        'message': '已开始故障诊断。请告诉我出现故障的设备名称/型号（例如：示波器 DS1054Z）。',
    })


@bp.route('/api/diagnosis/reply', methods=['POST'])
def diagnosis_reply():
    """向诊断会话发送用户消息，推进状态机。"""
    data = request.get_json(force=True, silent=True) or {}
    session_id = data.get('session_id', '')
    message = data.get('message', '')

    try:
        session = DiagnosisSession.load(session_id)
    except ValueError:
        return jsonify({'success': False, 'error': '非法的 session_id'}), 400
    if session is None:
        return jsonify({'success': False, 'error': '诊断会话不存在'}), 404

    try:
        result = session.advance(
            message,
            provider_id=data.get('provider_id'),
            model_id=data.get('model'),
        )
        return jsonify({'success': True, **result})
    except Exception as e:
        logger.error(f"[Diagnosis] 推进失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/diagnosis/<session_id>', methods=['GET'])
def diagnosis_status(session_id):
    """查看诊断会话状态。"""
    try:
        session = DiagnosisSession.load(session_id)
    except ValueError:
        return jsonify({'success': False, 'error': '非法的 session_id'}), 400
    if session is None:
        return jsonify({'success': False, 'error': '诊断会话不存在'}), 404
    return jsonify({'success': True, **session.to_dict()})
