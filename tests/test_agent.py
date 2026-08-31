"""v1.4 测试：安全硬规则、工具注册表、Agent 循环、故障诊断状态机。"""
import json
from types import SimpleNamespace

import pytest

from app.security.safety_rules import (
    assess_risk,
    build_safety_preamble,
    build_safety_system_constraint,
)
from app.agents.tools import execute_tool, list_tools
from app.agents.loop import run_agent
from app.agents.diagnosis import (
    DiagnosisSession,
    start_session,
    STATE_COLLECT_SYMPTOMS,
    STATE_STEP,
    STATE_DONE,
    MAX_STEPS,
)


# ---- 安全硬规则 ----

def test_high_risk_detection():
    r = assess_risk("我想带电操作检查一下 380V 配电柜的接线")
    assert r['level'] == 'high'
    assert '电气高压' in r['categories'] or '电源接线' in r['categories']


def test_medium_risk_detection():
    r = assess_risk("电烙铁焊接排针的时候温度设多少")
    assert r['level'] == 'medium'


def test_no_risk():
    r = assess_risk("Python 列表怎么排序")
    assert r['level'] == 'none'
    assert build_safety_preamble(r) == ""
    assert build_safety_system_constraint(r) == ""


def test_high_risk_preamble_and_constraint():
    r = assess_risk("浓硫酸稀释的时候可以把水倒进酸里吗")
    assert r['level'] == 'high'
    preamble = build_safety_preamble(r)
    assert '停止当前操作' in preamble
    assert '指导教师' in preamble
    constraint = build_safety_system_constraint(r)
    assert '不得提供' in constraint


def test_chat_stream_yields_safety_preamble_first(client, monkeypatch):
    """高风险问题：固定安全警示必须先于模型输出。"""
    from app import runtime

    def fake_stream(**kwargs):
        yield "模型的回答内容"

    monkeypatch.setattr(runtime, 'call_model_stream', fake_stream)
    r = client.post('/api/chat_stream', json={
        'message': '如何带电操作更换配电箱保险丝',
        'session_id': None,
    })
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert '安全提醒' in body
    assert body.index('安全提醒') < body.index('模型的回答内容')


def test_chat_stream_no_preamble_for_safe_question(client, monkeypatch):
    from app import runtime

    def fake_stream(**kwargs):
        yield "普通回答"

    monkeypatch.setattr(runtime, 'call_model_stream', fake_stream)
    r = client.post('/api/chat_stream', json={'message': '怎么用 numpy 求平均值'})
    assert r.status_code == 200
    assert '安全提醒' not in r.get_data(as_text=True)


# ---- 工具注册表 ----

def test_tool_registry_lists_core_tools():
    tools = list_tools()
    for name in ('search_knowledge_base', 'run_code', 'search_web', 'assess_safety_risk'):
        assert name in tools


def test_execute_unknown_tool():
    assert 'error' in execute_tool('no_such_tool', {})


def test_execute_tool_bad_json_arguments():
    assert 'error' in execute_tool('assess_safety_risk', '{broken json')


def test_assess_safety_risk_tool_runs_for_real():
    result = execute_tool('assess_safety_risk', {'operation': '高压电源带电接线'})
    assert result['level'] == 'high'


def test_search_kb_tool_reports_unavailable(monkeypatch):
    import app.services.kb as kb_service
    monkeypatch.setattr(kb_service, 'get_kb_instance', lambda kb_type: None)
    result = execute_tool('search_knowledge_base', {'query': 'x', 'kb_type': 'guide'})
    assert 'error' in result


# ---- Agent 循环（stub 客户端）----

def _tool_call(call_id, name, args):
    return SimpleNamespace(
        id=call_id, type='function',
        function=SimpleNamespace(name=name, arguments=json.dumps(args, ensure_ascii=False)),
    )


def _resp(content=None, tool_calls=None):
    msg = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


class _StubClient:
    """第一轮返回工具调用，第二轮返回最终回答。"""

    def __init__(self):
        self.calls = 0
        self.received_messages = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create))

    def _create(self, model, messages, tools):
        self.calls += 1
        self.received_messages = messages
        if self.calls == 1:
            return _resp(tool_calls=[
                _tool_call('c1', 'assess_safety_risk', {'operation': '高压接线'})])
        return _resp(content='最终回答：请先断电并联系教师。')


def test_run_agent_tool_loop():
    stub = _StubClient()
    result = run_agent(
        '高压接线怎么操作',
        model_id='stub-model',
        client_factory=lambda p, k, b: (stub, {'id': 'stub'}),
    )
    assert result['iterations'] == 2
    assert result['answer'].startswith('最终回答')
    assert len(result['tool_trace']) == 1
    trace = result['tool_trace'][0]
    assert trace['tool'] == 'assess_safety_risk'
    assert trace['result']['level'] == 'high'
    # 第二轮请求里应包含 tool 角色的结果消息
    roles = [m['role'] for m in stub.received_messages]
    assert 'tool' in roles


def test_run_agent_hits_iteration_limit():
    class _LoopingClient(_StubClient):
        def _create(self, model, messages, tools):
            self.calls += 1
            return _resp(tool_calls=[
                _tool_call(f'c{self.calls}', 'assess_safety_risk', {'operation': 'x'})])

    stub = _LoopingClient()
    result = run_agent('测试', model_id='m', max_iterations=3,
                       client_factory=lambda p, k, b: (stub, {'id': 's'}))
    assert result.get('truncated') is True
    assert len(result['tool_trace']) == 3


# ---- 故障诊断状态机（stub 话术生成器）----

def _gen(prompt, provider_id=None, model_id=None):
    if '引导用户描述故障现象' in prompt:
        return '请描述一下故障的具体表现。'
    if '诊断报告' in prompt:
        return '诊断报告：最可能原因是探头未校准。'
    return '排查步骤：请检查电源指示灯是否点亮，并告诉我结果。'


def test_diagnosis_full_flow():
    session = start_session()
    # 1. 确认设备
    r = session.advance('示波器 DS1054Z', generator=_gen)
    assert r['state'] == STATE_COLLECT_SYMPTOMS
    # 2. 描述现象（无风险）
    r = session.advance('开机后屏幕无波形显示', generator=_gen)
    assert r['state'] == STATE_STEP
    assert '排查步骤' in r['message']
    # 3. 反馈两轮
    r = session.advance('指示灯是亮的', generator=_gen)
    assert r['state'] == STATE_STEP
    # 4. 用户要求出报告
    r = session.advance('解决了，出报告吧', generator=_gen)
    assert r['state'] == STATE_DONE
    assert r.get('report') is True
    assert '诊断报告' in r['message']


def test_diagnosis_high_risk_symptom_gets_preamble():
    session = start_session()
    session.advance('直流电源', generator=_gen)
    r = session.advance('输出端冒烟，我想带电检查接线', generator=_gen)
    assert r['risk']['level'] == 'high'
    assert '安全提醒' in r['message']


def test_diagnosis_step_limit_forces_report():
    session = start_session()
    session.advance('万用表', generator=_gen)
    session.advance('测不出电压', generator=_gen)
    result = None
    for i in range(MAX_STEPS + 1):
        result = session.advance(f'第{i}次反馈：没解决', generator=_gen)
        if result['state'] == STATE_DONE:
            break
    assert result['state'] == STATE_DONE


def test_diagnosis_persistence_roundtrip():
    session = start_session()
    session.advance('信号发生器', generator=_gen)
    loaded = DiagnosisSession.load(session.session_id)
    assert loaded is not None
    assert loaded.device == '信号发生器'
    assert loaded.state == STATE_COLLECT_SYMPTOMS


def test_diagnosis_rejects_bad_session_id():
    with pytest.raises(ValueError):
        DiagnosisSession.load('../../etc')


# ---- API 端点 ----

def test_diagnosis_api_flow(client, monkeypatch):
    import app.agents.diagnosis as diag
    monkeypatch.setattr(diag, '_default_generator', _gen)

    r = client.post('/api/diagnosis/start')
    assert r.status_code == 200
    sid = r.get_json()['session_id']

    r = client.post('/api/diagnosis/reply', json={'session_id': sid, 'message': '示波器'})
    assert r.status_code == 200
    assert r.get_json()['state'] == STATE_COLLECT_SYMPTOMS

    r = client.get(f'/api/diagnosis/{sid}')
    assert r.status_code == 200
    assert r.get_json()['device'] == '示波器'


def test_diagnosis_api_bad_session(client):
    r = client.post('/api/diagnosis/reply', json={'session_id': '../../x', 'message': 'hi'})
    assert r.status_code == 400
    r = client.post('/api/diagnosis/reply', json={'session_id': 'diag_nonexistent00', 'message': 'hi'})
    assert r.status_code == 404


def test_agent_tools_endpoint(client):
    r = client.get('/api/agent/tools')
    assert r.status_code == 200
    assert 'search_knowledge_base' in r.get_json()['tools']


def test_agent_chat_requires_message(client):
    r = client.post('/api/agent/chat', json={})
    assert r.status_code == 400
