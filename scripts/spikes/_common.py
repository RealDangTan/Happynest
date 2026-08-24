"""Shared helpers cho spike scripts (phase 02).

Đọc backend/.env thủ công (KEY=VALUE từng dòng) để không phụ thuộc cwd, và hỗ trợ
bộ tên biến lệch hợp đồng §5 mà người dùng đang dùng (xem decisions.md 2026-08-24
— env alias): DATABASE_URL|DB_CONNECT_STRING, EMBEDDING_DIM|EMBEDDING_DIMENSIONS;
embeddings dùng EMBEDDING_BASE_URL/API_KEY nếu có, fallback sang LLM_*.

KHÔNG BAO GIỜ in giá trị key/password ra stdout hay file result.
"""

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / "backend" / ".env"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def utf8_stdio():
    """Ép UTF-8 cho stdout/stderr trên Windows console."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def load_env_file():
    data = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            data[key.strip()] = val.strip().strip('"').strip("'")
    # biến process-env (nếu có) ưu tiên hơn file
    for key in list(data):
        if os.environ.get(key):
            data[key] = os.environ[key]
    return data


def getenv(env, *names, default=None):
    for name in names:
        val = env.get(name)
        if val:
            return val
    return default


def db_params(env):
    """Trả kwargs cho psycopg.connect(), tách thủ công để né ký tự đặc biệt (@) trong password.

    Quy ước chuẩn: userinfo kết thúc ở ký tự '@' CUỐI CÙNG trước host.
    """
    url = getenv(env, "DATABASE_URL", "DB_CONNECT_STRING")
    if not url:
        raise RuntimeError("Thiếu DATABASE_URL/DB_CONNECT_STRING trong backend/.env")
    scheme_sep = url.find("://")
    if scheme_sep < 0:
        raise RuntimeError("DB URL thiếu scheme (giá trị bị che)")
    scheme = url[:scheme_sep]
    body = url[scheme_sep + 3:]
    userinfo, _, hostport_path = body.rpartition("@")
    user, _, password = userinfo.partition(":")
    hostport, _, path = hostport_path.partition("/")
    host, _, port = hostport.rpartition(":")
    dbname = path.split("?")[0]
    if scheme not in ("postgresql", "postgres", "postgresql+psycopg"):
        raise RuntimeError(f"Scheme DB không hỗ trợ: {scheme}")
    if not (host and port.isdigit() and user):
        raise RuntimeError("DB URL sai cấu trúc host:port/dbname (giá trị bị che)")
    return {
        "host": host,
        "port": int(port),
        "user": user,
        "password": password,
        "dbname": dbname or "postgres",
    }


def sqlalchemy_db_url(env):
    """URL dạng postgresql+psycopg:// với password percent-encoded (Phase 03+ dùng)."""
    from urllib.parse import quote

    p = db_params(env)
    return (
        f"postgresql+psycopg://{quote(p['user'])}:{quote(p['password'])}"
        f"@{p['host']}:{p['port']}/{p['dbname']}"
    )


def llm_client_cfg(env):
    cfg = {
        "base_url": getenv(env, "LLM_BASE_URL"),
        "api_key": getenv(env, "LLM_API_KEY"),
        "model": getenv(env, "LLM_MODEL"),
    }
    missing = [k for k in ("base_url", "api_key", "model") if not cfg[k]]
    if missing:
        raise RuntimeError(f"Thiếu LLM_* trong backend/.env: {missing}")
    return cfg


def embedding_cfg(env):
    dims_raw = getenv(env, "EMBEDDING_DIM", "EMBEDDING_DIMENSIONS", default="1536")
    return {
        "base_url": getenv(env, "EMBEDDING_BASE_URL", "LLM_BASE_URL"),
        "api_key": getenv(env, "EMBEDDING_API_KEY", "LLM_API_KEY"),
        "model": getenv(env, "EMBEDDING_MODEL", "LLM_MODEL"),
        "contract_dims": int(dims_raw),
    }


def save_result(name, payload):
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"{name}_result.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
