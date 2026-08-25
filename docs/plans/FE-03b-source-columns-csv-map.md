# FE-03b — Cột bật/tắt · Registry nguồn + Wizard · Map cột CSV — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xử lý 3 feedback của owner sau FE-03 (đã duyệt qua AskUserQuestion 2026-08-25, mọi lựa chọn = phương án Recommended): bảng cho bật/tắt cột; quản lý nguồn bằng registry BE nhẹ + wizard đăng ký 2 bước; import CSV có bước map cột thủ công kèm preview.

**Architecture:** Thêm bảng `sources` + 3 endpoint đọc/ghi nhẹ (KHÔNG đụng ingest — vẫn permissive). FE đổi field Nguồn thành Select + wizard con, thêm menu "Hiện thị cột" persist localStorage, biến tab CSV thành luồng 3 bước parse-map-preview chạy hoàn toàn phía client rồi serialize lại CSV chuẩn cho endpoint cũ.

**Tech Stack:** SQLAlchemy + Alembic (migration `0005`), FastAPI, TanStack Query v5, shadcn/ui (dropdown-menu + select + dialog đã có sẵn), papaparse (mới thêm).

**Spec:** [docs/decisions.md](../decisions.md) — entry "2026-08-25 — Duyệt đợt cải tiến FE-03b…" là phê duyệt phạm vi (spec gốc §4 không có sources).

## Global Constraints

- Ranh giới PII: KHÔNG gọi `include_raw=true`; chỉ hiển thị `sanitized_content`.
- Ingest permissive: POST /feedbacks + import-csv KHÔNG bị chặn khi source chưa đăng ký (non-goal đợt này).
- Không DELETE nguồn (chỉ PATCH is_active) — feedbacks trỏ source bằng string, xoá tên tạo orphan ý nghĩa.
- shadcn rules: `gap-*` không `space-y-*`; Empty/Skeleton/Badge/DropdownMenu thay markup tự chế; Dialog luôn có Title; semantic colors.
- Data fetch qua `lib/api.ts`; queryKey invalidate sau mutation; commit nhỏ conventional cuối mỗi task, trailer chuẩn repo.
- Lãnh thổ: `frontend/`, `backend/`, file `FE-*`, roadmap (edit tối thiểu, re-read trước khi ghi). KHÔNG đụng file `UF-*`.

---

### Task 1: BE — Model `Source` + migration `0005` + schemas + routes + tests

**Files:**
- Create: `backend/app/models/source.py`
- Modify: `backend/app/models/__init__.py` (thêm import + `__all__`)
- Create: `backend/alembic/versions/0005_sources.py` (revision `"0005"`, down_revision `"0004"`)
- Create: `backend/app/schemas/source.py`
- Create: `backend/app/api/routes/sources.py`
- Modify: file đăng ký router (tìm chỗ `include_router` của feedback — cùng kiểu đăng ký)
- Test: `backend/tests/test_sources_routes.py` (pytestmark integration, mẫu `test_auth.py`)

**Interfaces:**
- Produces: `GET /api/sources` → `list[SourceOut]`; `POST /api/sources` body `{name, description?}` → 201 `SourceOut` | 409 trùng tên; `PATCH /api/sources/{id}` body `{is_active}` → `SourceOut` | 404.
- `SourceOut`: `{id, name, description, is_active, created_at}`.

Model:

```python
"""Bảng sources — registry nguồn phản hồi (FE-03b, decisions 2026-08-25)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

Routes: dependency auth Y HỆT feedback routes (`get_current_user`); POST bắt IntegrityError → `HTTPException(409, "Nguồn đã tồn tại.")`; GET trả tất cả (cả inactive — UI tự lọc), order by name.

- [ ] Step 1: viết test integration CRUD trước (create → list có → dup 409 → PATCH inactive → GET lại thấy) — chạy FAIL
- [ ] Step 2: model + migration + schemas + routes đủ để PASS
- [ ] Step 3: `cd backend && uv run alembic upgrade head` trên DB dev thật; `uv run pytest tests/test_sources_routes.py -q` PASS; downgrade/upgrade sạch
- [ ] Step 4: commit `feat(backend): sources registry — model, endpoints, tests`

### Task 2: FE — Types/hook nguồn + Select nguồn & wizard đăng ký trong dialog nhập liệu

**Files:**
- Modify: `frontend/lib/types.ts` (+ `Source`)
- Create: `frontend/hooks/use-sources.ts` (query `["sources"]` staleTime 60s; mutations create/toggle invalidate key)
- Modify: `frontend/app/(app)/feedbacks/data-entry-dialog.tsx`

UI field Nguồn (tab Thủ công): `Select` liệt kê `sources.filter(isActive)`; item cuối `＋ Đăng ký nguồn mới…` mở **Dialog lồng 2 bước**: bước 1 form tên+mô tả (FieldGroup), bước 2 xác nhận → POST → chọn nguồn vừa tạo, toast success. Value nguồn giờ là state `sourceValue` (không còn FormData). Nếu danh sách rỗng → placeholder "Chọn hoặc đăng ký nguồn…".

- [ ] Step 1: hooks + types; Step 2: thay field + wizard; build xanh
- [ ] Step 3: verify tay qua curl `/api/sources` qua proxy; commit `feat(frontend): source select + register wizard in data entry`

### Task 3: FE — Menu "Hiện thị cột" persist localStorage

**Files:**
- Modify: `frontend/app/(app)/feedbacks/page.tsx`

Config cột: `content` (cố định) + toggle được: `source, created, severity, review, sentiment, ai_issue, confidence, pii`. Default hiện = 4 cột như cũ. localStorage key `feedbacks.columns` — đọc trong `useEffect` (tránh vỡ SSR), ghi mỗi lần đổi. Nhãn vi-VN: Cảm xúc (positive Tích cực / negative Tiêu cực / neutral Trung lập / mixed Trộn), AI issue (hallucination Ảo giác, inaccuracy Thiếu chính xác, bias Thiên vị, safety An toàn, privacy Quyền riêng tư, performance Hiệu năng, other Khác), Confidence (%), PII. Trigger: `Button variant="outline" size="sm"` + `Settings2` icon + `DropdownMenuCheckboxItem`.

- [ ] Step 1: implement + build xanh; commit `feat(frontend): column visibility toggle on feedbacks table`

### Task 4: FE — Import CSV 3 bước: chọn file → map cột → preview

**Files:**
- Modify: `frontend/package.json` (`pnpm add papaparse`, `-D @types/papaparse`)
- Create: `frontend/app/(app)/feedbacks/csv-import-wizard.tsx`
- Modify: `frontend/app/(app)/feedbacks/data-entry-dialog.tsx` (tab csv thay bằng component mới)

Luồng: chọn file → `Papa.parse(file, {header:true, skipEmptyLines:true})` → màn map: 4 trường mục tiêu (`source*`, `content*`, `external_ref`, `created_at`), mỗi trường một `Select` liệt kê cột file (optional có mục "-- Bỏ qua --"); auto-guess khớp thường trực + alias vi/en (`nội dung|text|review|comment…`). Submit bị chặn đến khi 2 trường bắt buộc được map. Preview bảng 5 dòng đầu đã transform; nút Import → `Papa.unparse` TOÀN bộ rows với header chuẩn → `new File(...)` → mutation FormData cũ (endpoint BE KHÔNG đổi). Ô created_at rỗng → bỏ qua để BE gán now().

- [ ] Step 1: cài papaparse; Step 2: wizard component; Step 3: build xanh + import thử file cột lệch tên qua UI API thật; commit `feat(frontend): csv import column mapping wizard`

### Task 5: Verify tổng + cập nhật board

- [ ] `pnpm --dir frontend build` xanh; pytest suite liên quan xanh
- [ ] Verify live: tạo nguồn qua wizard (curl), toggle cột (curl HTML không vỡ), import CSV map lạ
- [ ] Tick FE-00 board (dòng mới FE-03b ✅) + progress log; roadmap delivery-execute-plan thêm dòng P1 con; commit docs
- [ ] SendMessage báo session UF: UF-02 phần dialog/bảng đã lệch thực tế (cột toggle, wizard nguồn, CSV map) để họ cập nhật spec
