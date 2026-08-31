"""应用入口：python main.py

环境变量（详见 .env.example）：
- FLASK_HOST / FLASK_PORT   监听地址与端口（默认 127.0.0.1:5000，仅本机）
- FLASK_DEBUG               调试模式（默认关闭）
- AUTO_START_DOCKER         是否自动拉起 Docker/Piston（默认开启）
- PRELOAD_VL                是否预加载本地多模态模型（默认关闭）
- ADMIN_TOKEN               管理接口令牌（远程管理必须配置）
"""
import os

from app import create_app
from app.config import env_flag
from app.security import auth
from app.services.preload import preload_models
from app.services.sandbox import initialize_docker_and_piston


def main():
    # Docker/Piston 自动启动可通过环境变量关闭（AUTO_START_DOCKER=false），
    # 避免代码沙箱不可用时拖慢/阻塞 Web 服务启动
    if env_flag("AUTO_START_DOCKER", "true"):
        try:
            initialize_docker_and_piston()
        except Exception as e:
            print(f"⚠️  初始化 Docker/Piston 时出错: {e}")
            print("   应用将继续启动，但代码执行功能可能不可用")
    else:
        print("[info] AUTO_START_DOCKER=false，跳过 Docker/Piston 初始化")

    # 安全默认值：只监听本机。需要局域网访问时显式设置 FLASK_HOST=0.0.0.0
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    # debug 由环境变量控制，默认关闭（debug 模式会暴露交互式调试器，存在远程执行风险）
    debug = env_flag("FLASK_DEBUG")

    if host not in ("127.0.0.1", "localhost", "::1"):
        if not auth.ADMIN_TOKEN:
            print("⚠️  警告：正在监听非本机地址且未配置 ADMIN_TOKEN，")
            print("   局域网内任何人都无法访问管理接口（将被 403 拒绝）。")
            print("   如需远程管理，请在 .env 中设置 ADMIN_TOKEN。")
        if debug:
            print("⚠️  警告：debug 模式 + 非本机监听是高危组合，已强制关闭 debug")
            debug = False

    app = create_app()

    # 预加载模型（多模态模型可选）
    preload_models(preload_vl=env_flag("PRELOAD_VL"))

    print("\n" + "=" * 60)
    print("🎯 启动 Flask 服务器")
    print("=" * 60)
    print(f"请在浏览器访问 http://{host}:{port}")
    print("=" * 60 + "\n")
    # Windows 上 debug 模式建议关闭 reloader，避免重复绑定端口
    app.run(debug=debug, host=host, port=port, use_reloader=False)


if __name__ == '__main__':
    main()
