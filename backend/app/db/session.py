"""Engine + SessionLocal — Supabase session pooler (amendment v1.1).

- `search_path=extensions,public`: schema `extensions` là nơi Supabase cài
  extension `vector` (quy ước platform) — đặt trước để type `vector` resolve được.
- Pool 5+5: FE vault mở ~5 request song song ngay lúc mount; pool 2+2 cũ bắt
  3+ request xếp hàng chờ connection (mỗi RTT ~0.3s qua WAN — đo 2026-10-23).
  Session pooler free tier chịu tốt 10 conn; kết nối được tái sử dụng nên
  chi phí steady-state không đổi.
- `pool_recycle=1800`: Supabase ngắt conn idle lâu; thay conn già chủ động để
  `pool_pre_ping` ít khi phải hủy conn chết giữa request.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url_sqla,
    connect_args={"options": "-csearch_path=extensions,public"},
    pool_pre_ping=True,  # Supabase pooler ngắt conn idle → checkout chết 500; ping trước để tự thay conn mới
    pool_size=5,
    max_overflow=5,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
