"""
代码执行引擎
使用 Piston API 执行多种编程语言的代码
"""

import requests
import json
import os
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import urllib3

# 禁用不安全请求的警告（在使用 verify=False 时）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class ExecutionResult:
    """代码执行结果模型"""
    success: bool
    language: str
    version: str
    stdout: str
    stderr: str
    compile_output: Optional[str]
    run_time: float
    compile_time: Optional[float]
    exit_code: int
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'success': self.success,
            'language': self.language,
            'version': self.version,
            'output': self.stdout,
            'error': self.stderr,
            'compile_output': self.compile_output,
            'run_time': self.run_time,
            'compile_time': self.compile_time,
            'exit_code': self.exit_code
        }
    
    def format_for_display(self) -> str:
        """格式化输出用于显示"""
        lines = []
        
        # 编译信息
        if self.compile_output:
            if self.compile_time:
                lines.append(f"✓ 编译成功 (耗时: {self.compile_time:.2f}s)")
            lines.append(self.compile_output)
        
        # 执行信息
        lines.append(f"▶ 运行 {self.language} {self.version}")
        
        # 输出
        if self.stdout:
            lines.append("\n--- 标准输出 ---")
            lines.append(self.stdout)
        
        # 错误
        if self.stderr:
            lines.append("\n--- 错误输出 ---")
            lines.append(self.stderr)
        
        # 执行时间
        lines.append(f"\n✓ 执行完成 (耗时: {self.run_time:.2f}s, 退出码: {self.exit_code})")
        
        return '\n'.join(lines)


class CodeExecutor:
    """代码执行器，调用 Piston API"""
    
    def __init__(self, piston_url: str = None, timeout: int = 30):
        """
        初始化代码执行器
        
        Args:
            piston_url: Piston API URL
            timeout: 超时时间（秒）
        """
        self.piston_url = piston_url or os.getenv(
            'PISTON_API_URL',
            'http://localhost:2000/api/v2/execute'  # 默认使用本地
        )
        # 备用节点列表，当主节点返回 401 或失败时尝试
        self.mirror_nodes = [
            'http://localhost:2000/api/v2/execute',  # 本地 Docker 实例 (优先)
        ]
        # 只在本地不可用时才尝试在线节点
        self.online_fallback = os.getenv('PISTON_USE_ONLINE_FALLBACK', 'false').lower() == 'true'
        
        if self.online_fallback:
            self.mirror_nodes.extend([
                'https://piston.piston.sh/api/v2/execute',
                'https://piston.codefights.com/api/v2/execute',
                'https://piston.any.codes/api/v2/execute'
            ])
        
        self.timeout = timeout
        
        # 语言映射：前端语言名 -> Piston API 语言名
        self.language_map = {
            'python': 'python',
            'javascript': 'javascript',
            'java': 'java',
            'c': 'c',
            'cpp': 'cpp',
            'go': 'go',
            'rust': 'rust',
            'typescript': 'typescript'
        }
    
    def execute(self, code: str, language: str, version: str = "*") -> ExecutionResult:
        """
        执行代码
        
        Args:
            code: 源代码
            language: 语言名称 (python, java, c, cpp, javascript, go, rust, typescript)
            version: 语言版本 ("*" 表示最新版本)
        
        Returns:
            ExecutionResult: 执行结果
        """
        # 映射语言名称
        piston_language = self.language_map.get(language, language)
        
        # 如果版本是 "*"，尝试获取最新版本
        if version == "*":
            supported_langs = self.get_supported_languages()
            for lang_info in supported_langs:
                if lang_info['language'] == piston_language:
                    version = lang_info['version']
                    break
            # 如果还是 "*"，给一个通用的默认版本（虽然不推荐，但作为最后手段）
            if version == "*":
                defaults = {
                    'python': '3.10.0',
                    'javascript': '18.15.0',
                    'java': '17.0.2',
                    'c': '10.2.1',
                    'cpp': '10.2.1',
                    'go': '1.16.2',
                    'rust': '1.68.2',
                    'typescript': '5.0.3'
                }
                version = defaults.get(piston_language, "*")
        
        # 构建请求数据
        request_data = {
            "language": piston_language,
            "version": version,
            "files": [
                {
                    "content": code
                }
            ]
        }
        
        # 仅在提供 API Key 时尝试设置高级限制，否则使用 Piston 默认值
        # 注意：公共 API 通常不支持自定义内存限制和较长的超时时间，设置它们可能会导致 401 错误
        api_key = os.getenv('PISTON_API_KEY')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        if api_key:
            headers['Authorization'] = api_key
            request_data["compile_timeout"] = 10000
            request_data["run_timeout"] = self.timeout * 1000
            request_data["compile_memory_limit"] = -1
            request_data["run_memory_limit"] = 512 * 1024 * 1024
        else:
            # 对于公共 API，尽量使用最小参数集以避免触发 401
            pass
        
        # 尝试的 URL 列表（主节点 + 备用节点）
        urls_to_try = [self.piston_url] + self.mirror_nodes
        last_error = None
        local_piston_tried = False
        
        for current_url in urls_to_try:
            # 跳过重复的 URL
            if current_url in urls_to_try[:urls_to_try.index(current_url)]:
                continue
                
            is_local = 'localhost' in current_url or '127.0.0.1' in current_url
            
            try:
                # 尝试调用 Piston API
                response = self._make_request(current_url, request_data, headers)
                
                # 如果返回 401 且是主节点，尝试下一个镜像
                if response.status_code == 401 and current_url == self.piston_url:
                    print(f"[warn] Piston 主节点 {current_url} 提示未授权 (401)，正在尝试备用镜像...")
                    continue
                
                # 如果是本地 Piston 且返回错误，检查是否是语言包问题
                if is_local and response.status_code != 200:
                    local_piston_tried = True
                    try:
                        error_data = response.json()
                        if 'unknown' in str(error_data).lower():
                            print(f"[info] 本地 Piston 没有安装 {piston_language} 语言包")
                            continue
                    except:
                        pass
                    
                response.raise_for_status()
                
                # 解析响应
                result = response.json()
                return self._parse_response(result)
                
            except requests.exceptions.Timeout:
                last_error = f"代码执行超时（超过 {self.timeout} 秒）"
                if is_local:
                    local_piston_tried = True
                continue
            except requests.exceptions.ConnectionError as e:
                if is_local:
                    local_piston_tried = True
                    last_error = "本地 Piston 未运行或无法连接"
                else:
                    # 在线节点连接失败，静默跳过
                    continue
            except requests.exceptions.RequestException as e:
                # 如果是 401 错误，记录详细信息
                if hasattr(e, 'response') and e.response is not None and e.response.status_code == 401:
                    if is_local:
                        local_piston_tried = True
                    last_error = "API 需要授权"
                else:
                    if is_local:
                        local_piston_tried = True
                        last_error = f"本地 Piston 错误: {str(e)}"
                    # 在线节点错误，静默跳过
                continue
            except Exception as e:
                if is_local:
                    local_piston_tried = True
                    last_error = f"系统错误: {str(e)}"
                continue
        
        # 如果所有引擎都失败了
        if local_piston_tried:
            error_msg = f"本地 Piston 不可用。\n\n"
            error_msg += f"原因: {last_error}\n\n"
            error_msg += "💡 可能的原因：\n"
            error_msg += "1. Piston 容器未运行\n"
            error_msg += "   解决: 运行 python app.py 会自动启动\n"
            error_msg += "2. Piston 容器没有安装语言包\n"
            error_msg += f"   解决: 本地 Piston 暂不支持 {language}，请使用其他语言\n"
            error_msg += "3. 端口 2000 被占用\n"
            error_msg += "   解决: 修改 docker-compose.yml 中的端口映射\n\n"
            error_msg += "📝 当前支持的语言: Python, JavaScript, Java, C, C++, Go, Rust, TypeScript\n"
            error_msg += "   (需要手动安装语言包到 Piston 容器)"
        else:
            error_msg = f"代码执行服务暂时不可用。\n\n"
            error_msg += "💡 建议：\n"
            error_msg += "1. 确保 Docker 正在运行\n"
            error_msg += "2. 运行 python app.py 会自动启动 Piston\n"
            error_msg += "3. 手动启动: docker compose -p piston up -d"

        return ExecutionResult(
            success=False,
            language=language,
            version="unknown",
            stdout="",
            stderr=error_msg,
            compile_output=None,
            run_time=0.0,
            compile_time=None,
            exit_code=-1
        )
    
    def _make_request(self, url: str, data: dict, headers: dict) -> requests.Response:
        """发送 POST 请求，包含 SSL 容错逻辑"""
        try:
            # 正常尝试
            return requests.post(url, json=data, headers=headers, timeout=self.timeout + 5)
        except requests.exceptions.SSLError:
            # 如果 SSL 失败，尝试禁用验证（最后手段）
            print(f"[warn] {url} SSL 验证失败，尝试禁用验证...")
            return requests.post(url, json=data, headers=headers, timeout=self.timeout + 5, verify=False)

    def _make_get_request(self, url: str, headers: dict) -> requests.Response:
        """发送 GET 请求，包含 SSL 容错逻辑"""
        try:
            # 正常尝试
            return requests.get(url, headers=headers, timeout=10)
        except requests.exceptions.SSLError:
            # 如果 SSL 失败，尝试禁用验证（最后手段）
            print(f"[warn] {url} SSL 验证失败，尝试禁用验证...")
            return requests.get(url, headers=headers, timeout=10, verify=False)

    def _parse_response(self, response: dict) -> ExecutionResult:
        """
        解析 Piston API 响应
        
        Args:
            response: Piston API 响应数据
        
        Returns:
            ExecutionResult: 执行结果
        """
        language = response.get('language', 'unknown')
        version = response.get('version', 'unknown')
        
        # 获取运行结果
        run_data = response.get('run', {})
        stdout = run_data.get('stdout', '')
        stderr = run_data.get('stderr', '')
        exit_code = run_data.get('code', 0)
        output = run_data.get('output', '')
        
        # 如果 output 字段存在且包含内容，优先使用
        if output and not stdout:
            stdout = output
        
        # 获取编译结果（如果有）
        compile_data = response.get('compile')
        compile_output = None
        compile_time = None
        
        if compile_data:
            compile_stdout = compile_data.get('stdout', '')
            compile_stderr = compile_data.get('stderr', '')
            compile_code = compile_data.get('code', 0)
            
            # 如果编译失败
            if compile_code != 0:
                return ExecutionResult(
                    success=False,
                    language=language,
                    version=version,
                    stdout='',
                    stderr=compile_stderr or compile_stdout,
                    compile_output=compile_stderr or compile_stdout,
                    run_time=0.0,
                    compile_time=0.0,
                    exit_code=compile_code
                )
            
            compile_output = compile_stdout if compile_stdout else "编译成功"
            compile_time = 0.0  # Piston 不返回编译时间，使用占位值
        
        # 判断执行是否成功
        success = exit_code == 0 and not stderr
        
        # 计算运行时间（Piston 不返回，使用占位值）
        run_time = 0.0
        
        return ExecutionResult(
            success=success,
            language=language,
            version=version,
            stdout=stdout,
            stderr=stderr,
            compile_output=compile_output,
            run_time=run_time,
            compile_time=compile_time,
            exit_code=exit_code
        )
    
    def get_supported_languages(self) -> List[Dict]:
        """
        获取支持的语言列表
        
        Returns:
            List[Dict]: 语言列表，每个元素包含 language, version, aliases 等信息
        """
        # 尝试的 URL 列表
        urls_to_try = [self.piston_url] + self.mirror_nodes
        
        for current_url in urls_to_try:
            try:
                # Piston API 的 runtimes 端点
                runtimes_url = current_url.replace('/execute', '/runtimes')
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                response = self._make_get_request(runtimes_url, headers)
                
                # 如果是 401 且是主节点，跳过
                if response.status_code == 401 and current_url == self.piston_url:
                    continue
                    
                response.raise_for_status()
                
                runtimes = response.json()
                
                # 过滤出我们支持的语言
                supported = []
                for runtime in runtimes:
                    lang = runtime.get('language', '')
                    if lang in self.language_map.values():
                        supported.append({
                            'language': lang,
                            'version': runtime.get('version', 'unknown'),
                            'aliases': runtime.get('aliases', [])
                        })
                
                if supported:
                    return supported
                
            except Exception as e:
                print(f"尝试从 {current_url} 获取语言列表失败: {e}")
                continue
        
        # 如果所有节点都失败，返回默认支持的语言列表
        return [
            {'language': 'python', 'version': '3.10.0', 'aliases': ['py']},
            {'language': 'javascript', 'version': '18.15.0', 'aliases': ['js']},
            {'language': 'java', 'version': '15.0.2', 'aliases': []},
            {'language': 'c', 'version': '10.2.0', 'aliases': []},
            {'language': 'cpp', 'version': '10.2.0', 'aliases': ['c++']},
            {'language': 'go', 'version': '1.16.2', 'aliases': ['golang']},
            {'language': 'rust', 'version': '1.68.2', 'aliases': ['rs']},
            {'language': 'typescript', 'version': '5.0.3', 'aliases': ['ts']}
        ]


# 便捷函数
def execute_code(code: str, language: str, version: str = "*") -> Dict:
    """
    便捷函数：执行代码并返回字典结果
    
    Args:
        code: 源代码
        language: 语言名称
        version: 语言版本
    
    Returns:
        Dict: 执行结果字典
    """
    executor = CodeExecutor()
    result = executor.execute(code, language, version)
    return result.to_dict()
