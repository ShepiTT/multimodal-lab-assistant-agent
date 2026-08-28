#!/usr/bin/env python3
"""
为 Piston 安装常用语言包
"""

import requests
import time
import sys

PISTON_URL = "http://localhost:2000/api/v2"

# 要安装的语言和版本
LANGUAGES_TO_INSTALL = [
    {"language": "python", "version": "3.10.0"},
    {"language": "node", "version": "18.15.0"},  # JavaScript
    {"language": "java", "version": "15.0.2"},
    {"language": "gcc", "version": "10.2.0"},    # C
    # C++ 使用 gcc
]

def check_piston_available():
    """检查 Piston 是否可用"""
    try:
        response = requests.get(f"{PISTON_URL}/runtimes", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_available_packages():
    """获取可用的包列表"""
    try:
        response = requests.get(f"{PISTON_URL}/packages", timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"获取包列表失败: {e}")
        return []

def install_package(language, version):
    """安装指定的语言包"""
    print(f"\n📦 正在安装 {language} {version}...")
    
    try:
        # Piston API 安装包的端点
        url = f"{PISTON_URL}/packages"
        data = {
            "language": language,
            "version": version
        }
        
        response = requests.post(url, json=data, timeout=300)  # 5分钟超时
        
        if response.status_code == 200:
            result = response.json()
            if result.get('installed'):
                print(f"✅ {language} {version} 安装成功")
                return True
            else:
                print(f"⚠️  {language} {version} 安装状态未知")
                return False
        else:
            print(f"❌ {language} {version} 安装失败: {response.status_code}")
            print(f"   响应: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"⏱️  {language} {version} 安装超时（可能仍在后台安装）")
        return False
    except Exception as e:
        print(f"❌ {language} {version} 安装出错: {e}")
        return False

def check_installed_packages():
    """检查已安装的包"""
    try:
        response = requests.get(f"{PISTON_URL}/runtimes", timeout=10)
        if response.status_code == 200:
            runtimes = response.json()
            return runtimes
        return []
    except:
        return []

def main():
    print("="*60)
    print("🚀 Piston 语言包安装工具")
    print("="*60)
    print()
    
    # 检查 Piston 是否可用
    print("🔍 检查 Piston 服务...")
    if not check_piston_available():
        print("❌ Piston 服务不可用")
        print("   请确保 Piston 容器正在运行:")
        print("   docker compose -p piston up -d")
        sys.exit(1)
    
    print("✅ Piston 服务正常")
    print()
    
    # 获取可用包列表
    print("📋 获取可用包列表...")
    packages = get_available_packages()
    if not packages:
        print("❌ 无法获取包列表")
        sys.exit(1)
    
    print(f"✅ 找到 {len(packages)} 个可用包")
    print()
    
    # 检查当前已安装的包
    print("🔍 检查已安装的包...")
    installed = check_installed_packages()
    print(f"当前已安装 {len(installed)} 个语言")
    print()
    
    # 安装语言包
    print("="*60)
    print("开始安装语言包")
    print("="*60)
    print()
    print("⚠️  注意: 每个包的安装可能需要几分钟时间")
    print("   请耐心等待...")
    print()
    
    success_count = 0
    failed_count = 0
    
    for lang_info in LANGUAGES_TO_INSTALL:
        language = lang_info["language"]
        version = lang_info["version"]
        
        # 检查包是否存在
        package_exists = any(
            p["language"] == language and p["language_version"] == version
            for p in packages
        )
        
        if not package_exists:
            print(f"⚠️  {language} {version} 不在可用包列表中，跳过")
            continue
        
        # 检查是否已安装
        already_installed = any(
            r["language"] == language and r["version"] == version
            for r in installed
        )
        
        if already_installed:
            print(f"✅ {language} {version} 已安装，跳过")
            success_count += 1
            continue
        
        # 安装包
        if install_package(language, version):
            success_count += 1
            # 等待一下，避免过快请求
            time.sleep(2)
        else:
            failed_count += 1
    
    # 总结
    print()
    print("="*60)
    print("安装完成")
    print("="*60)
    print(f"✅ 成功: {success_count}")
    print(f"❌ 失败: {failed_count}")
    print()
    
    # 再次检查已安装的包
    print("🔍 验证安装结果...")
    installed = check_installed_packages()
    print(f"当前已安装 {len(installed)} 个语言:")
    for runtime in installed:
        print(f"  - {runtime['language']} {runtime['version']}")
    
    print()
    print("="*60)
    print("✨ 完成！")
    print("="*60)
    print()
    print("现在你可以使用代码执行功能了！")
    print("重启应用: python app.py")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  安装被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
