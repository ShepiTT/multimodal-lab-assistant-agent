"""
IDE 错误处理模块
统一处理各种错误类型
"""

from typing import Dict, Optional
from enum import Enum


class ErrorType(Enum):
    """错误类型枚举"""
    COMPILE_ERROR = "compile_error"
    RUNTIME_ERROR = "runtime_error"
    TIMEOUT_ERROR = "timeout_error"
    NETWORK_ERROR = "network_error"
    FILE_NOT_FOUND = "file_not_found"
    INVALID_FILENAME = "invalid_filename"
    PERMISSION_DENIED = "permission_denied"
    DISK_FULL = "disk_full"
    SESSION_NOT_FOUND = "session_not_found"
    SESSION_EXPIRED = "session_expired"
    API_UNAVAILABLE = "api_unavailable"
    LANGUAGE_NOT_SUPPORTED = "language_not_supported"
    RATE_LIMIT = "rate_limit"
    UNKNOWN_ERROR = "unknown_error"


def handle_execution_error(error_type: str, error_message: str, language: str = "") -> Dict:
    """
    处理代码执行错误
    
    Args:
        error_type: 错误类型
        error_message: 错误消息
        language: 编程语言
    
    Returns:
        Dict: 格式化的错误信息
    """
    error_handlers = {
        ErrorType.COMPILE_ERROR.value: lambda: {
            'type': 'compile_error',
            'message': f'编译失败',
            'detail': error_message,
            'suggestion': '请检查代码语法错误，注意分号、括号匹配等',
            'show_ai_button': True,
            'code': 400
        },
        ErrorType.RUNTIME_ERROR.value: lambda: {
            'type': 'runtime_error',
            'message': f'运行时错误',
            'detail': error_message,
            'suggestion': '请检查代码逻辑，如数组越界、空指针、除零等',
            'show_ai_button': True,
            'code': 400
        },
        ErrorType.TIMEOUT_ERROR.value: lambda: {
            'type': 'timeout_error',
            'message': '代码执行超时',
            'detail': error_message,
            'suggestion': '请优化代码或减少计算量，避免无限循环',
            'show_ai_button': False,
            'code': 408
        },
        ErrorType.NETWORK_ERROR.value: lambda: {
            'type': 'network_error',
            'message': '网络连接错误',
            'detail': error_message,
            'suggestion': '请检查网络连接或稍后重试',
            'show_ai_button': False,
            'code': 503
        }
    }
    
    handler = error_handlers.get(error_type, lambda: {
        'type': 'unknown_error',
        'message': '未知错误',
        'detail': error_message,
        'suggestion': '请联系管理员或稍后重试',
        'show_ai_button': False,
        'code': 500
    })
    
    return handler()


def handle_file_error(error_type: str, filename: str = "", detail: str = "") -> Dict:
    """
    处理文件操作错误
    
    Args:
        error_type: 错误类型
        filename: 文件名
        detail: 详细信息
    
    Returns:
        Dict: 格式化的错误信息
    """
    error_handlers = {
        ErrorType.FILE_NOT_FOUND.value: {
            'error': f'文件不存在: {filename}',
            'code': 404,
            'suggestion': '请检查文件名是否正确'
        },
        ErrorType.INVALID_FILENAME.value: {
            'error': f'文件名非法: {filename}',
            'code': 400,
            'suggestion': '文件名不能包含特殊字符: / \\ : * ? " < > |'
        },
        ErrorType.PERMISSION_DENIED.value: {
            'error': f'权限不足: {filename}',
            'code': 403,
            'suggestion': '您没有权限访问此文件'
        },
        ErrorType.DISK_FULL.value: {
            'error': '磁盘空间不足',
            'code': 507,
            'suggestion': '请删除一些文件或联系管理员',
            'detail': detail
        }
    }
    
    return error_handlers.get(error_type, {
        'error': f'文件操作错误: {detail}',
        'code': 500
    })


def handle_session_error(error_type: str, session_id: str = "") -> Dict:
    """
    处理会话错误
    
    Args:
        error_type: 错误类型
        session_id: 会话 ID
    
    Returns:
        Dict: 格式化的错误信息
    """
    error_handlers = {
        ErrorType.SESSION_NOT_FOUND.value: {
            'error': '会话不存在',
            'code': 404,
            'action': 'create_new_session',
            'message': '未找到您的会话，将创建新会话'
        },
        ErrorType.SESSION_EXPIRED.value: {
            'error': '会话已过期',
            'code': 410,
            'action': 'create_new_session',
            'message': '您的会话已超过7天未使用，已被自动清理'
        }
    }
    
    return error_handlers.get(error_type, {
        'error': '会话错误',
        'code': 500
    })


def handle_piston_error(status_code: int, response_text: str = "") -> Dict:
    """
    处理 Piston API 错误
    
    Args:
        status_code: HTTP 状态码
        response_text: 响应文本
    
    Returns:
        Dict: 格式化的错误信息
    """
    error_map = {
        400: {
            'error': '不支持的语言或参数错误',
            'suggestion': '请检查语言选择和代码格式',
            'code': 400
        },
        429: {
            'error': '请求过于频繁',
            'suggestion': '请稍后再试（每分钟最多10次）',
            'code': 429
        },
        503: {
            'error': 'Piston API 暂时不可用',
            'suggestion': '代码执行服务暂时不可用，请稍后重试',
            'code': 503
        }
    }
    
    return error_map.get(status_code, {
        'error': f'API 错误 ({status_code})',
        'detail': response_text,
        'suggestion': '请稍后重试或联系管理员',
        'code': status_code
    })


def format_error_message(error_dict: Dict) -> str:
    """
    格式化错误消息用于显示
    
    Args:
        error_dict: 错误字典
    
    Returns:
        str: 格式化的错误消息
    """
    lines = []
    
    if 'message' in error_dict:
        lines.append(f"❌ {error_dict['message']}")
    elif 'error' in error_dict:
        lines.append(f"❌ {error_dict['error']}")
    
    if 'detail' in error_dict and error_dict['detail']:
        lines.append(f"\n详细信息:\n{error_dict['detail']}")
    
    if 'suggestion' in error_dict:
        lines.append(f"\n💡 建议: {error_dict['suggestion']}")
    
    return '\n'.join(lines)


def is_compile_error(stderr: str, language: str) -> bool:
    """
    判断是否为编译错误
    
    Args:
        stderr: 错误输出
        language: 编程语言
    
    Returns:
        bool: 是否为编译错误
    """
    # 编译型语言的编译错误关键词
    compile_keywords = {
        'c': ['error:', 'fatal error:', 'undefined reference'],
        'cpp': ['error:', 'fatal error:', 'undefined reference'],
        'java': ['error:', 'cannot find symbol', 'class, interface, or enum expected'],
        'rust': ['error:', 'error[E'],
        'go': ['syntax error', 'undefined:']
    }
    
    if language not in compile_keywords:
        return False
    
    stderr_lower = stderr.lower()
    return any(keyword.lower() in stderr_lower for keyword in compile_keywords[language])


def extract_error_line(stderr: str, language: str) -> Optional[int]:
    """
    从错误信息中提取错误行号
    
    Args:
        stderr: 错误输出
        language: 编程语言
    
    Returns:
        Optional[int]: 错误行号，如果无法提取则返回 None
    """
    import re
    
    # 不同语言的行号模式
    patterns = {
        'python': r'line (\d+)',
        'java': r':(\d+):',
        'c': r':(\d+):',
        'cpp': r':(\d+):',
        'javascript': r':(\d+):',
        'typescript': r':(\d+):',
        'go': r':(\d+):',
        'rust': r':(\d+):'
    }
    
    pattern = patterns.get(language)
    if not pattern:
        return None
    
    match = re.search(pattern, stderr)
    if match:
        try:
            return int(match.group(1))
        except (ValueError, IndexError):
            return None
    
    return None
