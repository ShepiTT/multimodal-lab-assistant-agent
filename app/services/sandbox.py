"""Docker / Piston 代码沙箱的状态检查与启动。

只在入口脚本（main.py）显式调用初始化，Web 服务本身不依赖沙箱可用。
"""
import platform
import subprocess
import time
from pathlib import Path

from ..config import BASE_DIR


def check_docker_installed():
    """检查 Docker 是否安装"""
    try:
        result = subprocess.run(['docker', '--version'],
                                capture_output=True,
                                text=True,
                                timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_docker_running():
    """检查 Docker 是否运行"""
    try:
        result = subprocess.run(['docker', 'info'],
                                capture_output=True,
                                text=True,
                                timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def start_docker_desktop():
    """启动 Docker Desktop"""
    system = platform.system()
    try:
        if system == 'Windows':
            docker_path = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
            if Path(docker_path).exists():
                subprocess.Popen([docker_path],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                print("⏳ 正在启动 Docker Desktop，请稍候...")
                for _ in range(30):
                    time.sleep(1)
                    if check_docker_running():
                        print("✅ Docker Desktop 已启动")
                        return True
                print("⚠️  Docker Desktop 启动超时，请手动检查")
                return False
        elif system == 'Darwin':  # macOS
            subprocess.Popen(['open', '-a', 'Docker'],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            print("⏳ 正在启动 Docker Desktop，请稍候...")
            for _ in range(30):
                time.sleep(1)
                if check_docker_running():
                    print("✅ Docker Desktop 已启动")
                    return True
            return False
        else:  # Linux
            print("⚠️  请手动启动 Docker 服务: sudo systemctl start docker")
            return False
    except Exception as e:
        print(f"❌ 启动 Docker Desktop 失败: {e}")
        return False


def check_piston_running():
    """检查 Piston 容器是否运行"""
    try:
        result = subprocess.run(['docker', 'ps', '--filter', 'name=piston', '--format', '{{.Names}}'],
                                capture_output=True,
                                text=True,
                                timeout=5)
        return 'piston' in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def start_piston_container():
    """启动 Piston 容器"""
    try:
        print("📦 正在启动 Piston 容器...")
        result = subprocess.run(['docker', 'compose', '-p', 'piston', 'up', '-d'],
                                capture_output=True,
                                text=True,
                                timeout=60,
                                cwd=str(BASE_DIR))

        if result.returncode == 0:
            print("✅ Piston 容器已启动")
            time.sleep(3)
            return True
        else:
            print(f"⚠️  Piston 启动失败: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("⚠️  Piston 启动超时")
        return False
    except Exception as e:
        print(f"❌ 启动 Piston 失败: {e}")
        return False


def test_piston_connection():
    """测试 Piston 连接"""
    try:
        import requests
        response = requests.get('http://localhost:2000/api/v2/runtimes', timeout=5)
        if response.status_code == 200:
            runtimes = response.json()
            if len(runtimes) == 0:
                print("⚠️  Piston 连接正常，但没有安装语言包")
                print("   运行以下命令安装常用语言:")
                print("   python install_languages.py")
                return False
            else:
                print(f"✅ Piston 连接正常，支持 {len(runtimes)} 种语言")
                langs = set(r['language'] for r in runtimes)
                print(f"   已安装: {', '.join(sorted(langs))}")
                return True
        else:
            print(f"⚠️  Piston 响应异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️  Piston 连接测试失败: {e}")
        return False


def initialize_docker_and_piston():
    """初始化 Docker 和 Piston"""
    print("\n" + "=" * 60)
    print("🚀 初始化代码执行引擎")
    print("=" * 60)

    if not check_docker_installed():
        print("❌ Docker 未安装")
        print("   请访问 https://www.docker.com/products/docker-desktop 下载安装")
        print("   应用将继续启动，但代码执行功能不可用")
        return False

    print("✅ Docker 已安装")

    if not check_docker_running():
        print("📦 Docker 未运行，正在启动...")
        if not start_docker_desktop():
            print("❌ Docker 启动失败")
            print("   请手动启动 Docker Desktop")
            print("   应用将继续启动，但代码执行功能不可用")
            return False
    else:
        print("✅ Docker 正在运行")

    if not check_piston_running():
        print("📦 Piston 容器未运行，正在启动...")
        if not start_piston_container():
            print("❌ Piston 启动失败")
            print("   应用将继续启动，但代码执行功能不可用")
            return False
    else:
        print("✅ Piston 容器正在运行")

    test_piston_connection()

    print("=" * 60)
    print()
    return True
