"""
联网搜索模块

提供基于 Metaso API 的网页搜索功能，支持：
- 独立搜索接口
- 与聊天系统集成
- 搜索结果格式化
"""

from .search_api import (
    search_web,
    format_search_results,
    search_and_format
)

__all__ = [
    'search_web',
    'format_search_results',
    'search_and_format'
]

__version__ = '1.0.0'
