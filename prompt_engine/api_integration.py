"""
Prompt 引擎 API 集成模块
提供 Flask 路由和业务逻辑集成
"""

from flask import jsonify, request
from typing import Dict, Any, Optional
from .prompt_templates import get_prompt_engine, ScenarioType


def register_prompt_engine_routes(app):
    """
    注册 Prompt 引擎相关的 API 路由
    
    Args:
        app: Flask 应用实例
    """
    
    @app.route('/api/prompt_engine/scenarios', methods=['GET'])
    def get_scenarios():
        """获取所有支持的场景列表"""
        try:
            engine = get_prompt_engine()
            scenarios = engine.list_scenarios()
            return jsonify({
                "success": True,
                "scenarios": scenarios
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @app.route('/api/prompt_engine/generate', methods=['POST'])
    def generate_prompt():
        """
        生成场景化的系统提示词
        
        请求体：
        {
            "scenario": "operation_guide" | "fault_diagnosis" | "safety_regulation" | "code_debug",
            "user_context": {  // 可选
                "device": "设备名称",
                "version": "版本号"
            },
            "custom_constraints": [  // 可选
                "约束条件1",
                "约束条件2"
            ]
        }
        """
        try:
            data = request.get_json(force=True, silent=True) or {}
            scenario_str = data.get('scenario')
            user_context = data.get('user_context')
            custom_constraints = data.get('custom_constraints')
            
            if not scenario_str:
                return jsonify({
                    "success": False,
                    "error": "缺少 scenario 参数"
                }), 400
            
            # 转换场景类型
            try:
                scenario = ScenarioType(scenario_str)
            except ValueError:
                return jsonify({
                    "success": False,
                    "error": f"不支持的场景类型: {scenario_str}"
                }), 400
            
            engine = get_prompt_engine()
            prompt = engine.generate_prompt(
                scenario=scenario,
                user_context=user_context,
                custom_constraints=custom_constraints
            )
            
            scenario_info = engine.get_scenario_info(scenario)
            
            return jsonify({
                "success": True,
                "prompt": prompt,
                "scenario_info": scenario_info
            })
        
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @app.route('/api/prompt_engine/enhance_message', methods=['POST'])
    def enhance_message():
        """
        增强用户消息，添加场景特定的引导
        
        请求体：
        {
            "message": "用户原始消息",
            "scenario": "operation_guide" | "fault_diagnosis" | "safety_regulation" | "code_debug",
            "knowledge_base_context": "知识库上下文"  // 可选
        }
        """
        try:
            data = request.get_json(force=True, silent=True) or {}
            message = data.get('message', '').strip()
            scenario_str = data.get('scenario')
            kb_context = data.get('knowledge_base_context')
            
            if not message:
                return jsonify({
                    "success": False,
                    "error": "缺少 message 参数"
                }), 400
            
            if not scenario_str:
                return jsonify({
                    "success": False,
                    "error": "缺少 scenario 参数"
                }), 400
            
            # 转换场景类型
            try:
                scenario = ScenarioType(scenario_str)
            except ValueError:
                return jsonify({
                    "success": False,
                    "error": f"不支持的场景类型: {scenario_str}"
                }), 400
            
            engine = get_prompt_engine()
            enhanced_message = engine.enhance_user_message(
                user_message=message,
                scenario=scenario,
                knowledge_base_context=kb_context
            )
            
            return jsonify({
                "success": True,
                "original_message": message,
                "enhanced_message": enhanced_message
            })
        
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @app.route('/api/prompt_engine/scenario_info/<scenario_type>', methods=['GET'])
    def get_scenario_info(scenario_type: str):
        """获取特定场景的详细信息"""
        try:
            # 转换场景类型
            try:
                scenario = ScenarioType(scenario_type)
            except ValueError:
                return jsonify({
                    "success": False,
                    "error": f"不支持的场景类型: {scenario_type}"
                }), 400
            
            engine = get_prompt_engine()
            info = engine.get_scenario_info(scenario)
            
            if not info:
                return jsonify({
                    "success": False,
                    "error": "场景信息不存在"
                }), 404
            
            return jsonify({
                "success": True,
                "scenario_info": info
            })
        
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500


def detect_scenario_from_message(message: str) -> Optional[ScenarioType]:
    """
    从用户消息中自动检测场景类型（已禁用）
    
    Args:
        message: 用户消息
    
    Returns:
        ScenarioType: 始终返回 None（功能已禁用）
    """
    # 场景检测功能已被禁用
    return None


def integrate_with_chat_stream(
    user_message: str,
    scenario: Optional[ScenarioType] = None,
    auto_detect: bool = True,
    knowledge_base_context: Optional[str] = None
) -> tuple[str, Optional[str]]:
    """
    与聊天流式接口集成，自动增强消息和系统提示词
    
    Args:
        user_message: 用户原始消息
        scenario: 指定的场景类型（可选）
        auto_detect: 是否自动检测场景（默认 True，但已禁用）
        knowledge_base_context: 知识库上下文（可选）
    
    Returns:
        tuple: (增强后的消息, 场景化的系统提示词)
    """
    engine = get_prompt_engine()
    
    # 场景检测功能已被禁用，始终返回原始消息
    return user_message, None
    
    # 增强用户消息
    enhanced_message = engine.enhance_user_message(
        user_message=user_message,
        scenario=scenario,
        knowledge_base_context=knowledge_base_context
    )
    
    # 生成场景化的系统提示词
    system_prompt = engine.generate_prompt(scenario=scenario)
    
    return enhanced_message, system_prompt
