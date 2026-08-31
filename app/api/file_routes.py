"""文件上传与解析路由（统一经过 validate_and_save_upload 安全校验）。"""
from flask import Blueprint, jsonify, request

from .. import runtime
from ..config import UPLOAD_DIR, ensure_dirs
from ..security.validation import validate_and_save_upload

bp = Blueprint('file_routes', __name__)


@bp.route('/api/upload', methods=['POST'])
def upload():
    """上传文件接口，支持文档/图片/视频"""
    if 'file' not in request.files:
        return jsonify({"error": "缺少上传文件"}), 400

    ensure_dirs()
    try:
        safe_name, save_path, file_size, category = validate_and_save_upload(
            request.files['file'], UPLOAD_DIR)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    file_url = f"/uploads/{safe_name}"
    return jsonify({
        "success": True,
        "filename": safe_name,
        "file_url": file_url,
        "size": file_size,
        "category": category
    })


@bp.route('/api/upload_and_parse', methods=['POST'])
def upload_and_parse():
    """上传并解析文件，返回解析后的内容（与 /api/upload 使用同一套校验）"""
    if 'file' not in request.files:
        return jsonify({"error": "缺少上传文件"}), 400

    ensure_dirs()
    try:
        safe_name, save_path, file_size, category = validate_and_save_upload(
            request.files['file'], UPLOAD_DIR)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if runtime.parse_file is None:
        return jsonify({"error": "解析服务未加载"}), 500

    result = runtime.parse_file(str(save_path))

    if not result['success']:
        return jsonify({"error": result['error']}), 400

    return jsonify({
        "success": True,
        "filename": safe_name,
        "file_url": f"/uploads/{safe_name}",
        "type": result['type'],
        "content": result['content'] if result['type'] == 'text' else None,
        "media_info": result['content'] if result['type'] in ('image', 'video') else None
    })
