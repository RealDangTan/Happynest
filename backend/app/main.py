"""App factory FastAPI — skeleton Phase 03 (execute-plan §4).

Phase sau cắm vào khung này:
- Phase 04: routes auth + deps (get_current_user, require_role)
- Phase 05: routes feedback
- Phase 06: lifespan khởi tạo Presidio analyzer singleton
- Phase 07/08: LLM client, embedder; health mở rộng check DB + LLM mode
- Phase 09: routes analysis
"""

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routes import admin, analysis, auth, feedback, products
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import engine
from app.services import graph_runtime, llm_client, presidio_service, tracing

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 06 neo TẠI ĐÂY: khởi tạo Presidio analyzer singleton (instantiated once)
    # — Stanza vi+en nặng ~1GB RAM, KHÔNG được tạo lại mỗi request.
    presidio_service.init_presidio()
    # Tạo sớm 4 bảng checkpoint LangGraph (idempotent, ngoài filter Alembic) —
    # dùng chung cho graph HITL (hiện none sau strip; UNDERSTAND plan 25 tái sử
    # dụng). ⚠️ Chạy trong BACKGROUND THREAD, không await trực tiếp: lifespan
    # Windows dùng ProactorEventLoop mà async psycopg chỉ chạy trên selector
    # (quirk S5) — await ở đây nổ InterfaceError. Thread tự chạy asyncio.run
    # trên selector loop riêng; lỗi không chặn boot (health-degraded philosophy).
    threading.Thread(
        target=graph_runtime.ensure_checkpointer_ready,
        name="langgraph-checkpoint-setup",
        daemon=True,
    ).start()
    yield
    # Phase 07: flush batch trace Langfuse trước khi process thoát.
    tracing.flush()


_DEFAULT_SECRET_VALUES = {"", "changeme-openssl-rand-hex-32"}


def _enforce_secret_key(settings) -> None:
    """Phase 04: JWT đã bật — prod phải có SECRET_KEY thật; dev chỉ cảnh báo."""
    if settings.APP_ENV == "prod" and settings.SECRET_KEY in _DEFAULT_SECRET_VALUES:
        raise RuntimeError(
            "APP_ENV=prod nhưng SECRET_KEY chưa đặt/giữ giá trị mặc định — từ chối khởi động."
        )
    if settings.SECRET_KEY in _DEFAULT_SECRET_VALUES:
        logger.warning("SECRET_KEY đang dùng giá trị mặc định/dev — KHÔNG dùng cho prod.")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    _enforce_secret_key(settings)

    app = FastAPI(
        title="AI Feedback Agent",
        version="0.1.0",
        description="Backend foundation — khoa luan (phase skeleton)",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # ⚠️ PII rule: chỉ log method + path, KHÔNG log body/query của request.
        logger.error("unhandled error on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @app.get("/api/health", tags=["health"])
    def health():
        """Phase 07 mở rộng: check DB (SELECT 1) + trạng thái LLM client.

        `structured_output_mode`: "json_schema" | "prompt_json" | null khi chưa
        có call nào kể từ lúc process start (module state của llm_client).
        """
        db_status = "ok"
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:  # noqa: BLE001 — health không được raise
            db_status = "error"
            logger.error("health DB check failed: %s", type(exc).__name__)
        return {
            "status": "ok" if db_status == "ok" else "degraded",
            "app_env": settings.APP_ENV,
            "db": db_status,
            "structured_output_mode": llm_client._structured_output_mode,
            "llm_model": settings.LLM_MODEL or None,
            "embedding_model": settings.EMBEDDING_MODEL or None,
            "pii_mode": presidio_service.mode()["mode"],
        }

    app.include_router(admin.router)
    app.include_router(auth.router)
    # Phase 08: /similar — phase 05 mở rộng router này với CRUD ingestion + auth.
    app.include_router(feedback.router)
    # Phase 09: tạo run batch + progress/results API.
    app.include_router(analysis.router)
    # Plan 21 (VoC OS reshape): products = workspace scoping.
    app.include_router(products.router)

    return app


app = create_app()
