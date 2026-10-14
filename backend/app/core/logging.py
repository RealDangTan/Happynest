"""Logging chuẩn ứng dụng — stdlib logging, không thêm thư viện ngoài.

⚠️ QUY TẮC PII (AGENTS.md Hard Rule 2 — áp cho TOÀN BỘ app):
Logger KHÔNG BAO GIỜ nhận payload nội dung phản hồi (raw_content /
sanitized_content) hay bất kỳ giá trị secret nào (key, password).
Chỉ được log: id, metadata, số đếm, method + path. Mỗi lần review diff
phải kiểm tra lại rule này.
"""

import json
import logging
import re
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from traceback import extract_tb

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"

# Thư viện bên ngoài hay log ồn ào — hạ xuống WARNING
_QUIET_LOGGERS = ("httpx", "httpx2", "httpcore", "urllib3", "openai", "langfuse")

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)
run_id_context: ContextVar[str | None] = ContextVar("run_id", default=None)


class SafeJsonFormatter(logging.Formatter):
    """Export metadata only. Free text, exception messages and locals are omitted.

    An allowlist rather than regex redaction also protects arbitrary mixed VI/EN
    feedback that cannot reliably be recognized as sensitive text.
    """

    def format(self, record: logging.LogRecord) -> str:
        event = getattr(record, "event", "application_log")
        if event not in {"http_request", "http_error", "llm_call", "pipeline_execution"}:
            event = "application_log"
        data = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "service": "happynest-backend",
            "level": record.levelname,
            "logger": record.name[:160],
            "event": event,
        }
        for key, fallback in (("request_id", request_id_context.get()), ("run_id", run_id_context.get())):
            value = getattr(record, key, fallback)
            try:
                data[key] = str(uuid.UUID(str(value)))
            except (ValueError, TypeError, AttributeError):
                pass
        for key in ("status_code", "duration_ms", "prompt_tokens", "completion_tokens", "processed_count"):
            value = getattr(record, key, None)
            if isinstance(value, (float, int)) and not isinstance(value, bool):
                data[key] = value
        for key in ("method", "route", "pipeline", "outcome", "call_type", "error_type"):
            value = getattr(record, key, None)
            if isinstance(value, str) and len(value) <= 180 and re.fullmatch(r"[\w/{}.-]+", value):
                data[key] = value
        if record.exc_info and record.exc_info[0]:
            data["error_type"] = record.exc_info[0].__name__
            data["frames"] = [
                {"file": Path(frame.filename).name, "function": frame.name, "line": frame.lineno}
                for frame in extract_tb(record.exc_info[2])[-12:]
            ]
        return json.dumps(data, ensure_ascii=False, allow_nan=False)


def configure_logging(level: int = logging.INFO, *, log_dir: str = "storage/observability") -> None:
    root = logging.getLogger()
    # create_app() is also used in tests; never duplicate file writers or remove
    # the caller's capture handlers.
    for handler in list(root.handlers):
        if getattr(handler, "_happynest_handler", False):
            root.removeHandler(handler)
            handler.close()
    formatter = SafeJsonFormatter()
    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        directory / "events.jsonl", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.addFilter(lambda record: record.name.startswith(("app.", "understand_agent", "happynest.")))
    for handler in (logging.StreamHandler(), file_handler):
        handler.setFormatter(formatter)
        handler._happynest_handler = True
        root.addHandler(handler)
    root.setLevel(level)
    for name in _QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    # Uvicorn's default access lines include raw URLs/query strings. Our ASGI
    # request event replaces them, including when launched by a normal uvicorn CLI.
    logging.getLogger("uvicorn.access").disabled = True
    for name in ("uvicorn", "uvicorn.error"):
        for handler in logging.getLogger(name).handlers:
            handler.setFormatter(formatter)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
