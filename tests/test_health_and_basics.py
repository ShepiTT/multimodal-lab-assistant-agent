"""健康检查、可观测性与基础接口行为测试。"""


def test_health_live(client):
    r = client.get('/health/live')
    assert r.status_code == 200
    assert r.get_json()['status'] == 'ok'


def test_health_ready_reports_llm_state(client):
    r = client.get('/health/ready')
    assert r.status_code in (200, 503)
    body = r.get_json()
    assert 'llm_runner' in body


def test_health_capabilities_lists_all_subsystems(client):
    r = client.get('/health/capabilities')
    assert r.status_code == 200
    caps = r.get_json()
    for key in ('llm', 'rag', 'prompt_engine', 'asr', 'ocr', 'tts',
                'web_search', 'docker', 'code_sandbox', 'admin_token_configured'):
        assert key in caps, f"capabilities 缺少 {key}"


def test_request_id_header_present(client):
    r = client.get('/health/live')
    assert r.headers.get('X-Request-ID')


def test_api_404_returns_json(client):
    r = client.get('/api/nonexistent')
    assert r.status_code == 404
    assert r.get_json()['error'] == 'Not Found'


def test_api_405_returns_json(client):
    r = client.get('/api/chat')  # chat 只接受 POST
    assert r.status_code == 405
    assert r.get_json()['error'] == 'Method Not Allowed'


def test_chat_requires_message(client):
    r = client.post('/api/chat', json={})
    assert r.status_code == 400


def test_chat_stream_requires_message(client):
    r = client.post('/api/chat_stream', json={})
    assert r.status_code == 400


def test_llm_config_readable(client):
    r = client.get('/api/llm_config')
    assert r.status_code == 200
    assert 'providers' in r.get_json()


def test_system_prompt_readable(client):
    r = client.get('/api/system_prompt')
    assert r.status_code == 200


def test_new_session_returns_id(client):
    r = client.post('/api/session/new')
    assert r.status_code == 200
    assert r.get_json()['session_id']


def test_history_list(client):
    r = client.get('/api/history')
    assert r.status_code == 200
    assert 'history' in r.get_json()


def test_web_search_status(client):
    r = client.get('/api/web_search/status')
    assert r.status_code == 200
    assert 'available' in r.get_json()
