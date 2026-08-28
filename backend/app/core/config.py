"""Application settings đọc từ backend/.env — env contract execute-plan §5.

⚠️ QUY TẮC PII/SECRET (AGENTS.md Hard Rule 2): module này KHÔNG BAO GIỜ được
log/print giá trị của SECRET_KEY, LLM_API_KEY, DATABASE_URL... Chỉ tên biến
được phép xuất hiện trong log.

Alias env (decisions.md 2026-08-24): chấp nhận cả tên chuẩn lẫn tên người dùng
từng điền — DATABASE_URL|DB_CONNECT_STRING, EMBEDDING_DIM|EMBEDDING_DIMENSIONS.
"""

from functools import lru_cache
from urllib.parse import quote

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # .env người dùng có thể dư biến — không chết app
    )

    # --- App ---
    APP_ENV: str = "dev"
    SECRET_KEY: str = ""  # Phase 04 enforce bắt buộc khi bật JWT
    CORS_ORIGINS: str = "http://localhost:3000"

    # --- Database ---
    DATABASE_URL: str = Field(
        validation_alias=AliasChoices("DATABASE_URL", "DB_CONNECT_STRING"),
    )

    # --- LLM provider (OpenAI-compatible) ---
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""
    EMBEDDING_BASE_URL: str = ""  # nếu rỗng → fallback LLM_BASE_URL (Phase 08)
    EMBEDDING_API_KEY: str = ""   # nếu rỗng → fallback LLM_API_KEY
    EMBEDDING_MODEL: str = ""
    EMBEDDING_DIM: int = Field(
        default=1536,
        validation_alias=AliasChoices("EMBEDDING_DIM", "EMBEDDING_DIMENSIONS"),
    )

    # --- Pipeline thresholds ---
    CLASSIFY_CONFIDENCE_REVIEW_BELOW: float = 0.60
    HIGH_SEVERITY_CONFIDENCE_REVIEW_BELOW: float = 0.75
    # Phase 13 stretch: few-shot từ correction gần nhất — TĂNG chi phí token,
    # mặc định TẮT (plan 13 §3.5).
    CLASSIFY_FEWSHOT_ENABLED: bool = False

    # --- Clustering trend (Phase 14, hằng số chốt cứng plan §3 Task 2) ---
    CLUSTER_MIN_SIZE: int = 10        # min_cluster_size HDBSCAN (S4 sweep {5,10,15})
    CLUSTER_WINDOW_DAYS: int = 30     # cửa sổ "hiện tại" cho trend
    CLUSTER_SPIKE_RATIO: float = 2.0
    CLUSTER_SPIKE_MIN_CURRENT: int = 5
    CLUSTER_EMERGING_MIN: int = 3

    # --- Insight engine (Phase 15): cap số cụm xử lý mỗi lượt run để kiềm chế
    # chi phí LLM (spec §8 rủi ro "hết tín dụng") ---
    INSIGHT_MAX_CLUSTERS: int = 10

    # --- Agent graph (Phase 19): biên an toàn chốt cứng plan §2 — router
    # LLM tự do chọn bước nhưng bị khóa trong 2 trần này ---
    AGENT_MAX_STEPS: int = 12              # vượt cap → buộc nhánh finish
    AGENT_LLM_BUDGET_PER_RUN: int = 24     # COUNT llm_call_logs trước MỌI call tốn LLM
    AGENT_TOP_CLUSTERS: int = 3            # số target tối đa mỗi run
    AGENT_RISK_PRIORITY_THRESHOLD: float = 0.70   # risk gate: suggested_priority ≥
    AGENT_RISK_SEVERITY_SHARE: float = 0.30       # risk gate: share(high,critical) ≥

    # --- LISTEN import (plan 22): raw CSV lưu DISK local (decisions
    # 2026-08-28 — chưa có Supabase Storage credentials) ---
    IMPORT_STORAGE_DIR: str = "storage/imports"

    # --- Closed-loop impact (Phase 20): cửa sổ đo trước/sau mốc ticket draft ---
    IMPACT_WINDOW_DAYS: int = 7

    # --- Tracing (Langfuse Cloud EU) ---
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = "https://cloud.langfuse.com"
    LANGFUSE_TRACING_ENABLED: bool = True
    PROMPT_VERSION: str = "v1"

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS_ORIGINS là chuỗi phân tách phẩy trong .env → list cho middleware."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def database_url_sqla(self) -> str:
        """DATABASE_URL chuẩn hóa thành URL SQLAlchemy psycopg, userinfo percent-encoded.

        Password Supabase có thể chứa '@' ':' '/' — tách userinfo ở ký tự '@'
        CUỐI CÙNG (RFC 3986) rồi percent-encode, cùng cách
        `scripts/spikes/_common.py::sqlalchemy_db_url` đã chạy PASS ở spike S3/S6.
        """
        url = self.DATABASE_URL.strip()
        scheme_sep = url.find("://")
        if scheme_sep < 0:
            raise ValueError("DATABASE_URL thiếu scheme (postgresql:// hoặc postgresql+psycopg://)")
        scheme_raw = url[:scheme_sep]
        body = url[scheme_sep + 3 :]
        if scheme_raw in ("postgres", "postgresql"):
            scheme = "postgresql+psycopg"
        elif scheme_raw == "postgresql+psycopg":
            scheme = scheme_raw
        else:
            raise ValueError(f"Scheme DB không hỗ trợ: {scheme_raw}")
        userinfo, sep, hostport_path = body.rpartition("@")
        if not sep or not userinfo:
            return f"{scheme}://{body}"
        user, _, password = userinfo.partition(":")
        return (
            f"{scheme}://{quote(user, safe='')}:{quote(password, safe='')}"
            f"@{hostport_path}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
