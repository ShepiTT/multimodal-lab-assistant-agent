"""页面与静态资源路由。

注意：不再把项目根目录挂成静态目录（旧版 static_folder='.' 会让
/./.env 直接下载出所有密钥），只暴露 ui/、uploads/、voice_data/ 三个受控目录。
"""
from flask import Blueprint, render_template, send_from_directory

from ..config import BASE_DIR, FAVICON_FILE, UPLOAD_DIR, VOICE_DATA_DIR

bp = Blueprint('static_routes', __name__)


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/ide')
def ide_page():
    """IDE 主页面"""
    return render_template('templates/ide.html')


@bp.route('/ui/<path:filename>')
def serve_ui(filename):
    return send_from_directory(BASE_DIR / 'ui', filename)


@bp.route('/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@bp.route('/voice_data/<path:filename>')
def serve_voice_data(filename):
    return send_from_directory(VOICE_DATA_DIR, filename)


@bp.route('/favicon.ico')
def favicon():
    # 提供站点图标，若无文件则返回 204 避免 404 噪声
    if FAVICON_FILE.exists():
        return send_from_directory(BASE_DIR, 'favicon.ico')
    return ("", 204)
