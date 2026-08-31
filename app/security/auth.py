"""管理接口鉴权。

- 配置了 ADMIN_TOKEN：管理接口必须携带匹配的 X-Admin-Token 请求头。
- 未配置 ADMIN_TOKEN：仅允许来自本机回环地址的请求（本地单人使用场景）。
"""
import functools
import os

from flask import jsonify, request

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "").strip()


def require_admin(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if ADMIN_TOKEN:
            provided = request.headers.get('X-Admin-Token', '')
            if not provided or provided != ADMIN_TOKEN:
                return jsonify({'error': '管理接口需要有效的 X-Admin-Token'}), 401
        else:
            remote = request.remote_addr or ''
            if remote not in ('127.0.0.1', '::1', 'localhost'):
                return jsonify({'error': '管理接口未配置 ADMIN_TOKEN，仅允许本机访问'}), 403
        return func(*args, **kwargs)
    return wrapper
