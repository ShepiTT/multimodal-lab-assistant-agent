"""管理配置路由：系统提示词、场景提示词、环境配置状态。写操作需管理鉴权。"""
import os

from flask import Blueprint, jsonify, request

from .. import runtime
from ..config import (
    load_system_prompt_config,
    save_system_prompt_config,
    timestamp,
)
from ..observability import get_logger
from ..security.auth import require_admin

bp = Blueprint('admin_routes', __name__)
logger = get_logger()

_SCENARIOS = ('operation_guide', 'fault_diagnosis', 'safety_regulation', 'code_debug')


@bp.route('/api/system_prompt', methods=['GET'])
def api_get_system_prompt():
    """获取系统提示词配置"""
    config = load_system_prompt_config()
    return jsonify(config)


@bp.route('/api/system_prompt', methods=['POST'])
@require_admin
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


@bp.route('/api/env/config', methods=['GET'])
def api_get_env_config():
    """获取各厂商 API 的配置状态。

    安全约束：绝不返回 API Key 明文，只返回是否已配置（has_config）
    以及非敏感的 base_url。密钥仅保存在服务端环境变量中。
    """
    try:
        config = {
            'qwen': {
                'base_url': os.getenv('ALI_BASE_URL', ''),
                'has_config': bool(os.getenv('ALI_API_KEY'))
            },
            'openai': {
                'base_url': os.getenv('OPENAI_BASE_URL', ''),
                'has_config': bool(os.getenv('OPENAI_API_KEY'))
            },
            'volcengine': {
                'base_url': os.getenv('APK_BASE_URL', ''),
                'has_config': bool(os.getenv('ARK_API_KEY'))
            },
            'deepseek': {
                'base_url': os.getenv('DEEPSEEK_BASE_URL', ''),
                'has_config': bool(os.getenv('DEEPSEEK_API_KEY'))
            },
            'local': {
                'base_url': os.getenv('LOCAL_LLM_BASE_URL', ''),
                'has_config': bool(os.getenv('LOCAL_LLM_BASE_URL'))
            }
        }

        return jsonify({
            'success': True,
            'config': config
        })

    except Exception as e:
        logger.error(f"读取环境配置失败: {e}")
        return jsonify({'error': '读取环境配置失败'}), 500


def _scenario_map():
    return {
        'operation_guide': runtime.ScenarioType.OPERATION_GUIDE,
        'fault_diagnosis': runtime.ScenarioType.FAULT_DIAGNOSIS,
        'safety_regulation': runtime.ScenarioType.SAFETY_REGULATION,
        'code_debug': runtime.ScenarioType.CODE_DEBUG
    }


@bp.route('/api/scenario/prompt', methods=['GET'])
def api_get_scenario_prompt():
    """获取指定场景的提示词"""
    scenario = request.args.get('scenario')

    if not scenario:
        return jsonify({'error': '缺少 scenario 参数'}), 400

    if not runtime.PROMPT_ENGINE_AVAILABLE or not runtime.get_prompt_engine:
        return jsonify({'error': 'Prompt 引擎未加载'}), 500

    try:
        scenario_map = _scenario_map()
        if scenario not in scenario_map:
            return jsonify({'error': '无效的场景类型'}), 400

        # 先尝试从配置文件读取自定义提示词
        config = load_system_prompt_config()
        custom_prompt = None

        if 'scenario_prompts' in config and scenario in config['scenario_prompts']:
            custom_prompt = config['scenario_prompts'][scenario].get('prompt')

        if custom_prompt:
            prompt = custom_prompt
        else:
            engine = runtime.get_prompt_engine()
            prompt = engine.generate_prompt(scenario_map[scenario])

        return jsonify({
            'success': True,
            'scenario': scenario,
            'prompt': prompt,
            'is_custom': bool(custom_prompt)
        })

    except Exception as e:
        logger.error(f"获取场景提示词失败: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/scenario/prompt', methods=['POST'])
@require_admin
def api_save_scenario_prompt():
    """保存指定场景的提示词"""
    data = request.get_json(force=True, silent=True) or {}
    scenario = data.get('scenario')
    prompt = data.get('prompt')

    if not scenario or prompt is None:
        return jsonify({'error': '缺少必要参数'}), 400

    if scenario not in _SCENARIOS:
        return jsonify({'error': '无效的场景类型'}), 400

    try:
        config = load_system_prompt_config()

        if 'scenario_prompts' not in config:
            config['scenario_prompts'] = {}

        config['scenario_prompts'][scenario] = {
            'prompt': prompt,
            'updated_at': timestamp()
        }

        save_system_prompt_config(config)

        return jsonify({
            'success': True,
            'message': '提示词已保存'
        })

    except Exception as e:
        logger.error(f"保存场景提示词失败: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/scenario/prompt/default', methods=['GET'])
def api_get_default_scenario_prompt():
    """获取指定场景的默认提示词"""
    scenario = request.args.get('scenario')

    if not scenario:
        return jsonify({'error': '缺少 scenario 参数'}), 400

    if not runtime.PROMPT_ENGINE_AVAILABLE or not runtime.get_prompt_engine:
        return jsonify({'error': 'Prompt 引擎未加载'}), 500

    try:
        scenario_map = _scenario_map()
        if scenario not in scenario_map:
            return jsonify({'error': '无效的场景类型'}), 400

        engine = runtime.get_prompt_engine()
        prompt = engine.generate_prompt(scenario_map[scenario])

        return jsonify({
            'success': True,
            'scenario': scenario,
            'prompt': prompt
        })

    except Exception as e:
        logger.error(f"获取默认场景提示词失败: {e}")
        return jsonify({'error': str(e)}), 500
