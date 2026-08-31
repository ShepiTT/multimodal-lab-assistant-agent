"""知识库路由：文件管理、索引构建、语义检索。写操作需管理鉴权。"""
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request

from .. import runtime
from ..config import KB_BASE_DIR, LOG_DIR
from ..observability import get_logger
from ..security.auth import require_admin
from ..security.validation import (
    KB_UPLOAD_ALLOWED_EXTS,
    resolve_kb_folder,
    validate_and_save_upload,
)
from ..services import kb as kb_service
from ..services.kb import get_kb_instance, load_kb_json, save_kb_json

bp = Blueprint('knowledge_routes', __name__)
logger = get_logger()


def _format_size(size: int) -> str:
    return f"{size / 1024:.1f}KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f}MB"


@bp.route('/api/kb/files', methods=['GET'])
def kb_list_files():
    """获取知识库文件列表，从 text.json 读取"""
    kb_type = request.args.get('type', 'guide')
    kb_folder = resolve_kb_folder(kb_type)
    if kb_folder is None:
        return jsonify({"success": False, "error": f"无效的知识库类型: {kb_type}"}), 400
    kb_data_dir = KB_BASE_DIR / kb_folder / "data"

    if not kb_data_dir.exists():
        return jsonify({"success": True, "files": [], "index_built": False, "total_chunks": 0})

    kb_data = load_kb_json(kb_type)
    files_in_json = {f['name']: f for f in kb_data.get('files', [])}

    # 检查索引文件是否真实存在
    index_file = KB_BASE_DIR / kb_folder / "index" / "index.pkl"
    actual_index_built = index_file.exists()

    # 如果 JSON 中说索引已构建，但实际文件不存在，更新状态
    if kb_data.get('index_built', False) and not actual_index_built:
        logger.info(f"[KB] 检测到索引文件已删除，更新状态: {kb_type}")
        kb_data['index_built'] = False
        kb_data['total_chunks'] = 0
        save_kb_json(kb_type, kb_data)
        kb_service._kb_instances.pop(kb_type, None)

    # 同步实际文件系统中的文件
    actual_files = []
    for file_path in kb_data_dir.iterdir():
        if file_path.is_file() and file_path.name != 'text.json':
            stat = file_path.stat()

            if file_path.name in files_in_json:
                file_info = files_in_json[file_path.name].copy()
                file_info['size'] = _format_size(stat.st_size)
            else:
                file_info = {
                    "id": str(uuid.uuid4())[:8],
                    "name": file_path.name,
                    "type": "文档",
                    "size": _format_size(stat.st_size),
                    "chars": 0,
                    "recall": 0,
                    "date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "enabled": True,
                    "status": "pending",
                    "batch": datetime.fromtimestamp(stat.st_mtime).strftime("%Y%m%d%H%M")
                }

            actual_files.append(file_info)

    kb_data['files'] = actual_files
    save_kb_json(kb_type, kb_data)

    return jsonify({
        "success": True,
        "files": actual_files,
        "index_built": kb_data.get('index_built', False),
        "total_chunks": kb_data.get('total_chunks', 0)
    })


@bp.route('/api/kb/upload', methods=['POST'])
@require_admin
def kb_upload_files():
    """上传文件到知识库"""
    kb_type = request.form.get('kb_type', 'guide')
    kb_folder = resolve_kb_folder(kb_type)
    if kb_folder is None:
        return jsonify({"success": False, "error": f"无效的知识库类型: {kb_type}"}), 400
    kb_data_dir = KB_BASE_DIR / kb_folder / "data"
    kb_data_dir.mkdir(parents=True, exist_ok=True)

    files = request.files.getlist('files')
    if not files:
        return jsonify({"success": False, "error": "没有上传文件"}), 400

    kb_data = load_kb_json(kb_type)
    existing_files = {f['name']: f for f in kb_data.get('files', [])}

    uploaded = []
    errors = []
    for file in files:
        if file.filename:
            try:
                safe_name, save_path, _, _ = validate_and_save_upload(
                    file, kb_data_dir, allowed_exts=KB_UPLOAD_ALLOWED_EXTS)
            except ValueError as e:
                errors.append(f"{file.filename}: {e}")
                continue
            uploaded.append(safe_name)

            stat = save_path.stat()
            if safe_name not in existing_files:
                existing_files[safe_name] = {
                    "id": str(uuid.uuid4())[:8],
                    "name": safe_name,
                    "type": "文档",
                    "size": _format_size(stat.st_size),
                    "chars": 0,
                    "recall": 0,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "enabled": True,
                    "status": "pending",
                    "batch": datetime.now().strftime("%Y%m%d%H%M")
                }

    kb_data['files'] = list(existing_files.values())
    kb_data['index_built'] = False  # 上传新文件后需要重新构建索引
    save_kb_json(kb_type, kb_data)

    resp = {"success": True, "uploaded": uploaded, "message": f"已上传 {len(uploaded)} 个文件"}
    if errors:
        resp["errors"] = errors
    return jsonify(resp)


@bp.route('/api/kb/build', methods=['POST'])
@require_admin
def kb_build_index():
    """构建知识库索引"""
    if not runtime.KB_AVAILABLE:
        return jsonify({"success": False, "error": "知识库模块未加载"}), 500

    data = request.get_json(force=True, silent=True) or {}
    kb_type = data.get('kb_type', 'guide')
    chunk_method = data.get('chunk_method', 'smart')  # 默认使用智能切分
    chunk_size = int(data.get('chunk_size', 500))

    kb_folder = resolve_kb_folder(kb_type)
    if kb_folder is None:
        return jsonify({"success": False, "error": f"无效的知识库类型: {kb_type}"}), 400
    kb_dir = KB_BASE_DIR / kb_folder

    try:
        kb_service._kb_instances.pop(kb_type, None)

        kb_data = load_kb_json(kb_type)
        enabled_files = [
            f['name'] for f in kb_data.get('files', [])
            if f.get('enabled', True)
        ]

        logger.info(f"[KB] 构建索引: kb_type={kb_type}, 启用文件={enabled_files}")

        if not enabled_files:
            return jsonify({"success": False, "error": "没有启用的文件"}), 400

        kb = runtime.FaultDiagnosisKnowledgeBase(
            data_dir=str(kb_dir),
            chunk_method=chunk_method,
            chunk_size=chunk_size,
            device=None  # 自动检测 GPU
        )

        source_dir = str(kb_dir / 'data')
        kb.build_index(source_dir=source_dir, enabled_files=enabled_files)
        kb_service._kb_instances[kb_type] = kb

        total_chunks = kb.vector_store.index.ntotal if kb.vector_store else 0

        kb_data['index_built'] = True
        kb_data['total_chunks'] = total_chunks

        # 统计每个文件的字符数和块数
        file_stats = {}
        if kb.vector_store and hasattr(kb.vector_store, 'metadata'):
            for metadata in kb.vector_store.metadata:
                source = metadata.get('source', '')
                if source:
                    if source not in file_stats:
                        file_stats[source] = {'chars': 0, 'chunks': 0}
                    file_stats[source]['chars'] += metadata.get('length', 0)
                    file_stats[source]['chunks'] += 1

        for file_info in kb_data.get('files', []):
            filename = file_info['name']
            if file_info.get('enabled', True):
                file_info['status'] = 'completed'
                if filename in file_stats:
                    file_info['chars'] = file_stats[filename]['chars']
                    file_info['chunks'] = file_stats[filename]['chunks']
            else:
                file_info['status'] = 'pending'

        save_kb_json(kb_type, kb_data)

        return jsonify({
            "success": True,
            "message": "索引构建完成",
            "total_docs": total_chunks
        })
    except Exception as e:
        logger.error(f"[KB] 构建索引失败: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/api/kb/search', methods=['POST'])
def kb_search():
    """知识库检索"""
    if not runtime.KB_AVAILABLE:
        return jsonify({"success": False, "error": "知识库模块未加载"}), 500

    data = request.get_json(force=True, silent=True) or {}
    query = (data.get('query') or '').strip()
    kb_type = data.get('kb_type', 'guide')
    top_k = int(data.get('top_k', 5))
    threshold = float(data.get('threshold', 0.0))
    use_rewrite = data.get('use_rewrite', False)  # 是否启用查询改写

    if not query:
        return jsonify({"success": False, "error": "查询内容不能为空"}), 400

    kb = get_kb_instance(kb_type)
    if not kb:
        return jsonify({"success": False, "error": f"知识库 {kb_type} 未加载或不存在"}), 404

    try:
        # 查询改写
        rewritten_query = query
        if use_rewrite:
            try:
                from models.LLM.query_rewriter import rewrite_query
                rewritten_query = rewrite_query(query)
                logger.info(f"[KB] 查询改写: '{query}' -> '{rewritten_query}'")
                LOG_DIR.mkdir(exist_ok=True)
                with open(LOG_DIR / "query_rewrite.log", 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                            f"[KB] 查询改写: '{query}' -> '{rewritten_query}'\n")
            except Exception as e:
                logger.warning(f"[KB] 查询改写失败，使用原查询: {e}")

        results = kb.search(rewritten_query, top_k=top_k)

        # 过滤低于阈值的结果
        filtered_results = []
        recalled_files = {}  # 统计每个文件被召回的次数

        for r in results:
            if r['score'] >= threshold:
                source_file = r['metadata'].get('source', 'unknown')
                recalled_files[source_file] = recalled_files.get(source_file, 0) + 1

                filtered_results.append({
                    "content": r['document'],
                    "score": round(r['score'], 4),
                    "file": source_file,
                    "title": r['metadata'].get('title', ''),
                    "chunk_id": r['metadata'].get('chunk_id', 0)
                })

        # 更新召回次数到 text.json
        if recalled_files:
            kb_data = load_kb_json(kb_type)
            for file_info in kb_data.get('files', []):
                filename = file_info['name']
                if filename in recalled_files:
                    file_info['recall'] = file_info.get('recall', 0) + recalled_files[filename]
            save_kb_json(kb_type, kb_data)

        response_data = {
            "success": True,
            "results": filtered_results,
            "total": len(filtered_results)
        }

        if use_rewrite and rewritten_query != query:
            response_data["rewritten_query"] = rewritten_query

        return jsonify(response_data)
    except Exception as e:
        logger.error(f"[KB] 检索失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/api/kb/status', methods=['GET'])
def kb_status():
    """获取知识库状态"""
    kb_type = request.args.get('type', 'guide')
    kb_folder = resolve_kb_folder(kb_type)
    if kb_folder is None:
        return jsonify({"success": False, "error": f"无效的知识库类型: {kb_type}"}), 400
    kb_dir = KB_BASE_DIR / kb_folder
    index_file = kb_dir / "index" / "index.pkl"
    data_dir = kb_dir / "data"

    kb_data = load_kb_json(kb_type)
    file_count = len(kb_data.get('files', []))

    status = {
        "kb_type": kb_type,
        "kb_available": runtime.KB_AVAILABLE,
        "index_exists": index_file.exists(),
        "data_dir_exists": data_dir.exists(),
        "file_count": file_count,
        "loaded": kb_type in kb_service._kb_instances,
        "doc_count": 0
    }

    if index_file.exists():
        try:
            cached = kb_service._kb_instances.get(kb_type)
            if cached and cached.vector_store:
                status["doc_count"] = cached.vector_store.index.ntotal
            else:
                import pickle
                with open(index_file, 'rb') as f:
                    index_data = pickle.load(f)
                    if 'index' in index_data:
                        status["doc_count"] = index_data['index'].ntotal
        except Exception as e:
            logger.warning(f"[KB] 读取索引文件失败: {e}")
            status["doc_count"] = kb_data.get('total_chunks', 0)
    else:
        if kb_type in kb_service._kb_instances:
            del kb_service._kb_instances[kb_type]
            logger.info(f"[KB] 索引文件不存在，已清除缓存: {kb_type}")
        status["doc_count"] = 0

    return jsonify(status)


@bp.route('/api/kb/delete', methods=['POST'])
@require_admin
def kb_delete_file():
    """删除知识库文件"""
    data = request.get_json(force=True, silent=True) or {}
    kb_type = data.get('kb_type', 'guide')
    filename = data.get('filename', '')

    if not filename:
        return jsonify({"success": False, "error": "文件名不能为空"}), 400

    kb_folder = resolve_kb_folder(kb_type)
    if kb_folder is None:
        return jsonify({"success": False, "error": f"无效的知识库类型: {kb_type}"}), 400
    kb_dir = KB_BASE_DIR / kb_folder

    # 路径越界防护：只允许删除 data 目录内的直接文件
    kb_data_dir = (kb_dir / "data").resolve()
    file_path = (kb_data_dir / filename).resolve()
    if file_path.parent != kb_data_dir:
        return jsonify({"success": False, "error": "非法的文件名"}), 400

    if file_path.exists():
        file_path.unlink()

        kb_data = load_kb_json(kb_type)
        kb_data['files'] = [f for f in kb_data.get('files', []) if f['name'] != filename]

        # 如果没有文件了，删除索引
        if not kb_data['files']:
            kb_data['index_built'] = False
            kb_data['total_chunks'] = 0

            index_dir = kb_dir / "index"
            if index_dir.exists():
                import shutil
                shutil.rmtree(index_dir)
                logger.info(f"[KB] 已删除索引目录: {index_dir}")
        else:
            kb_data['index_built'] = False

        save_kb_json(kb_type, kb_data)

        kb_service._kb_instances.pop(kb_type, None)

        return jsonify({"success": True, "message": "文件已删除"})

    return jsonify({"success": False, "error": "文件不存在"}), 404


@bp.route('/api/kb/clear_cache', methods=['POST'])
@require_admin
def kb_clear_cache():
    """清除知识库缓存"""
    data = request.get_json(force=True, silent=True) or {}
    kb_type = data.get('kb_type', 'all')

    if kb_type == 'all':
        cleared = list(kb_service._kb_instances.keys())
        kb_service._kb_instances.clear()
        logger.info(f"[KB] 已清除所有知识库缓存: {cleared}")
        return jsonify({"success": True, "message": "已清除所有知识库缓存", "cleared": cleared})
    else:
        if kb_type in kb_service._kb_instances:
            del kb_service._kb_instances[kb_type]
            return jsonify({"success": True, "message": f"已清除 {kb_type} 知识库缓存"})
        else:
            return jsonify({"success": True, "message": f"{kb_type} 知识库未缓存"})
