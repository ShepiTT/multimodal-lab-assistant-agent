"""结构化日志与请求追踪。

- 每个请求分配 request_id，响应头带 X-Request-ID，日志行自动携带。
- 日志同时输出到 log/app.log（JSON 行，便于机器解析）和控制台（人类可读）。
- after_request 记录访问日志：方法、路径、状态码、耗时。
"""
import json
import logging
import time
import uuid

from flask import g, has_request_context, request

from ..config import LOG_DIR

_LOGGER_NAME = "labagent"


class _JsonFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        req_id = getattr(record, "request_id", None)
        if req_id:
            entry["request_id"] = req_id
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


class _RequestIdFilter(logging.Filter):
    """把当前请求的 request_id 注入每条日志记录。"""

    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = g.get("request_id") if has_request_context() else None
        return True


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)


def setup_observability(app):
    LOG_DIR.mkdir(exist_ok=True)

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        file_handler = logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")
        file_handler.setFormatter(_JsonFormatter())
        file_handler.addFilter(_RequestIdFilter())
        logger.addHandler(file_handler)

        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", "%H:%M:%S"))
        console.addFilter(_RequestIdFilter())
        logger.addHandler(console)

    @app.before_request
    def _assign_request_id():
        g.request_id = uuid.uuid4().hex[:12]
        g.request_start = time.time()

    @app.after_request
    def _access_log(response):
        response.headers["X-Request-ID"] = g.get("request_id", "-")
        # 静态资源不记访问日志，避免噪声
        if request.path.startswith(("/api/", "/health/")):
            elapsed_ms = int((time.time() - g.get("request_start", time.time())) * 1000)
            logger.info(f"{request.method} {request.path} {response.status_code} {elapsed_ms}ms")
        return response
