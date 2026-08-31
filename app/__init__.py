"""应用工厂：组装 Flask 实例、蓝图、可观测性与统一错误处理。"""
from flask import Flask, jsonify, request
from flask_compress import Compress

from .config import BASE_DIR


def create_app() -> Flask:
    # 模板根目录指向项目根（index.html 与 templates/ide.html 都相对项目根引用）。
    # 有意不设置 static_folder：旧版把项目根挂成静态目录，导致 /./.env 可直接
    # 下载出全部密钥。静态资源统一由 static_routes 中的受控路由提供。
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR),
        static_folder=None,
    )

    # 启用 Gzip 压缩 - 可以将响应体积减少 60-70%
    Compress(app)

    # 可观测性：request_id、访问日志、结构化日志
    from .observability.logging import setup_observability
    setup_observability(app)

    # 注册各蓝图
    from .api import (
        admin_routes,
        agent_routes,
        chat_routes,
        file_routes,
        ide_routes,
        knowledge_routes,
        speech_routes,
        static_routes,
    )
    from .observability import health

    app.register_blueprint(static_routes.bp)
    app.register_blueprint(chat_routes.bp)
    app.register_blueprint(admin_routes.bp)
    app.register_blueprint(file_routes.bp)
    app.register_blueprint(speech_routes.bp)
    app.register_blueprint(knowledge_routes.bp)
    app.register_blueprint(ide_routes.bp)
    app.register_blueprint(agent_routes.bp)
    app.register_blueprint(health.bp)

    # Prompt 引擎自带的路由注册（外部模块，可选）
    from . import runtime
    if runtime.PROMPT_ENGINE_AVAILABLE and runtime.register_prompt_engine_routes:
        try:
            runtime.register_prompt_engine_routes(app)
            print("[info] Prompt 引擎路由已注册")
        except Exception as e:
            print(f"[warn] 注册 Prompt 引擎路由失败: {e}")

    # 统一错误响应：API 路径返回 JSON，页面路径保持默认行为
    def _wants_json() -> bool:
        return request.path.startswith(('/api/', '/health/'))

    @app.errorhandler(404)
    def _not_found(e):
        if _wants_json():
            return jsonify({'error': 'Not Found', 'path': request.path}), 404
        return e

    @app.errorhandler(405)
    def _method_not_allowed(e):
        if _wants_json():
            return jsonify({'error': 'Method Not Allowed', 'path': request.path}), 405
        return e

    @app.errorhandler(500)
    def _internal_error(e):
        if _wants_json():
            return jsonify({'error': 'Internal Server Error'}), 500
        return e

    return app
