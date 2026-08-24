"""Logging chuẩn ứng dụng — stdlib logging, không thêm thư viện ngoài.

⚠️ QUY TẮC PII (AGENTS.md Hard Rule 2 — áp cho TOÀN BỘ app):
Logger KHÔNG BAO GIỜ nhận payload nội dung phản hồi (raw_content /
sanitized_content) hay bất kỳ giá trị secret nào (key, password).
Chỉ được log: id, metadata, số đếm, method + path. Mỗi lần review diff
phải kiểm tra lại rule này.
"""

import logging

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"

# Thư viện bên ngoài hay log ồn ào — hạ xuống WARNING
_QUIET_LOGGERS = ("httpx", "httpcore", "urllib3", "openai", "langfuse")


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format=LOG_FORMAT)
    for name in _QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
