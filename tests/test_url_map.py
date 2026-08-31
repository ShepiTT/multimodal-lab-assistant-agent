"""路由完整性回归：重构后的应用必须注册与拆分前完全一致的路由。

基线取自拆分前 app.py 的 url_map 快照（54 条），唯一有意的差异是移除了
`/./<path:filename>`——旧版把项目根目录挂成静态目录，导致 /./.env 可以
直接下载出全部密钥。
"""

EXPECTED_RULES = {
    "/ GET",
    "/api/agent/chat POST",
    "/api/agent/tools GET",
    "/api/asr POST",
    "/api/diagnosis/<session_id> GET",
    "/api/diagnosis/reply POST",
    "/api/diagnosis/start POST",
    "/api/chat POST",
    "/api/chat_stream POST",
    "/api/chat_with_file POST",
    "/api/env/config GET",
    "/api/history GET",
    "/api/ide/debug POST",
    "/api/ide/files GET",
    "/api/ide/files POST",
    "/api/ide/files/<filename> DELETE",
    "/api/ide/files/<filename> GET",
    "/api/ide/files/<filename> PUT",
    "/api/ide/files/rename POST",
    "/api/ide/languages GET",
    "/api/ide/run POST",
    "/api/ide/session POST",
    "/api/ide/session/<session_id> DELETE",
    "/api/ide/session/<session_id> GET",
    "/api/ide/session/<session_id> PUT",
    "/api/kb/build POST",
    "/api/kb/clear_cache POST",
    "/api/kb/delete POST",
    "/api/kb/files GET",
    "/api/kb/search POST",
    "/api/kb/status GET",
    "/api/kb/upload POST",
    "/api/llm_config GET",
    "/api/ocr POST",
    "/api/prompt_engine/enhance_message POST",
    "/api/prompt_engine/generate POST",
    "/api/prompt_engine/scenario_info/<scenario_type> GET",
    "/api/prompt_engine/scenarios GET",
    "/api/scenario/prompt GET",
    "/api/scenario/prompt POST",
    "/api/scenario/prompt/default GET",
    "/api/session/<session_id> DELETE",
    "/api/session/new POST",
    "/api/system_prompt GET",
    "/api/system_prompt POST",
    "/api/tts POST",
    "/api/upload POST",
    "/api/upload_and_parse POST",
    "/api/web_search POST",
    "/api/web_search/status GET",
    "/favicon.ico GET",
    "/health/capabilities GET",
    "/health/live GET",
    "/health/ready GET",
    "/ide GET",
    "/ui/<path:filename> GET",
    "/uploads/<path:filename> GET",
    "/voice_data/<path:filename> GET",
}


def _current_rules(app):
    rules = set()
    for r in app.url_map.iter_rules():
        methods = sorted(m for m in r.methods if m not in ('HEAD', 'OPTIONS'))
        rules.add(f"{r.rule} {','.join(methods)}")
    return rules


def test_all_expected_routes_registered(app):
    current = _current_rules(app)
    missing = EXPECTED_RULES - current
    assert not missing, f"重构后缺失路由: {sorted(missing)}"


def test_no_unexpected_routes(app):
    current = _current_rules(app)
    extra = current - EXPECTED_RULES
    assert not extra, f"出现未预期的新路由: {sorted(extra)}"


def test_root_static_route_removed(app):
    """旧版 static_folder='.' 产生的 /./<path> 路由必须消失。"""
    for r in app.url_map.iter_rules():
        assert not r.rule.startswith("/./"), f"项目根静态路由仍然存在: {r.rule}"
