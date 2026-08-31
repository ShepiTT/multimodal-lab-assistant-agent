"""安全回归测试：v1.1 修复的所有漏洞在重构后必须保持修复状态。"""
import io

import pytest

from app.config import UPLOAD_DIR
from app.security import auth


LAN_ADDR = {'REMOTE_ADDR': '192.168.1.50'}


# ---- 密钥泄露防护 ----

def test_env_config_never_returns_api_key(client):
    r = client.get('/api/env/config')
    assert r.status_code == 200
    body = r.get_json()
    for provider, cfg in (body.get('config') or {}).items():
        assert 'api_key' not in cfg, f"{provider} 返回了 api_key 字段"
        assert 'has_config' in cfg


def test_dotenv_not_downloadable(client):
    """旧版 /./.env 能直接下载出密钥文件，必须永远返回 404。"""
    for path in ('/./.env', '/./config.py', '/./main.py', '/.env'):
        r = client.get(path)
        assert r.status_code == 404, f"{path} 返回了 {r.status_code}"


# ---- 管理接口鉴权 ----

def test_admin_write_allowed_from_loopback_without_token(client):
    r = client.post('/api/system_prompt', json={})
    assert r.status_code == 200


def test_admin_write_rejected_from_lan_without_token(client):
    r = client.post('/api/system_prompt', json={}, environ_overrides=LAN_ADDR)
    assert r.status_code == 403


def test_admin_token_matrix(client, monkeypatch):
    monkeypatch.setattr(auth, 'ADMIN_TOKEN', 'test-token-123')
    # 正确 token → 放行
    r = client.post('/api/system_prompt', json={}, environ_overrides=LAN_ADDR,
                    headers={'X-Admin-Token': 'test-token-123'})
    assert r.status_code == 200
    # 错误 token → 401
    r = client.post('/api/system_prompt', json={}, environ_overrides=LAN_ADDR,
                    headers={'X-Admin-Token': 'wrong'})
    assert r.status_code == 401
    # 配置了 token 后，本机不带 token 也拒绝
    r = client.post('/api/system_prompt', json={})
    assert r.status_code == 401


@pytest.mark.parametrize("method,path,payload", [
    ('post', '/api/kb/upload', None),
    ('post', '/api/kb/build', {}),
    ('post', '/api/kb/delete', {'kb_type': 'guide', 'filename': 'x.pdf'}),
    ('post', '/api/kb/clear_cache', {}),
    ('post', '/api/scenario/prompt', {'scenario': 'code_debug', 'prompt': 'x'}),
])
def test_admin_endpoints_reject_lan(client, method, path, payload):
    kwargs = {'environ_overrides': LAN_ADDR}
    if payload is not None:
        kwargs['json'] = payload
    r = getattr(client, method)(path, **kwargs)
    assert r.status_code == 403, f"{path} 未拒绝局域网访问: {r.status_code}"


# ---- 路径穿越防护 ----

def test_kb_type_traversal_rejected(client):
    assert client.get('/api/kb/files?type=../../data').status_code == 400
    assert client.get('/api/kb/status?type=..').status_code == 400


def test_kb_delete_filename_traversal_rejected(client):
    r = client.post('/api/kb/delete', json={'kb_type': 'guide', 'filename': '../../main.py'})
    assert r.status_code == 400


def test_ide_session_id_traversal_rejected(client):
    r = client.get('/api/ide/files?session_id=../../../etc')
    assert r.status_code == 400
    r = client.get('/api/ide/session/..%2F..%2Fetc')
    assert r.status_code in (400, 404)


# ---- 上传校验 ----

def _upload(client, path, filename, content):
    return client.post(path, data={
        'file': (io.BytesIO(content), filename)
    }, content_type='multipart/form-data')


def test_upload_rejects_forged_extension(client):
    r = _upload(client, '/api/upload', 'fake.png', b'this is not a png')
    assert r.status_code == 400


def test_upload_rejects_disallowed_extension(client):
    r = _upload(client, '/api/upload_and_parse', 'evil.sh', b'#!/bin/sh\nrm -rf /')
    assert r.status_code == 400


def test_upload_rejects_empty_file(client):
    r = _upload(client, '/api/upload', 'empty.txt', b'')
    assert r.status_code == 400


def test_upload_accepts_valid_png_with_random_suffix(client):
    png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
    r = _upload(client, '/api/upload', 'real.png', png)
    assert r.status_code == 200
    fn = r.get_json()['filename']
    assert fn.startswith('real_') and fn.endswith('.png') and len(fn) > len('real_.png')
    # 清理测试产物
    p = UPLOAD_DIR / fn
    if p.exists():
        p.unlink()
