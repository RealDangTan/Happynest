"""App factory FastAPI — skeleton Phase 03 (execute-plan §4).

Phase sau cắm vào khung này:
- Phase 04: routes auth + deps (get_current_user, require_role)
- Phase 05: routes feedback
- Phase 06: lifespan khởi tạo Presidio analyzer singleton
- Phase 07/08: LLM client, embedder; health mở rộng check DB + LLM mode
- Phase 09: routes analysis
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import admin
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 06 neo TẠI ĐÂY: khởi tạo Presidio analyzer singleton (instantiated once).
    yield
    # Phase 07 neo TẠI ĐÂY: langfuse.shutdown() trước khi process thoát.


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

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
        """Bản sơ khai Phase 03 — Phase 08 mở rộng: check DB + LLM structured mode."""
        return {"status": "ok", "app_env": settings.APP_ENV}

    app.include_router(admin.router)

    return app


app = create_app()
