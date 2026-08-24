"""Engine + SessionLocal — Supabase session pooler (amendment v1.1).

- `search_path=extensions,public`: schema `extensions` là nơi Supabase cài
  extension `vector` (quy ước platform) — đặt trước để type `vector` resolve được.
- Pool nhỏ 2+2 phù hợp free tier qua internet (WAN ~50–200ms/query).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url_sqla,
    connect_args={"options": "-csearch_path=extensions,public"},
    pool_size=2,
    max_overflow=2,
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
