# Handoff — 2026-10-12 — ZCode: importer mapping G1 đơn giản hoá + Stepper dùng chung + quyết định All-TEXT

## Đã làm

1. **Stepper dùng chung** — extract `Stepper` khỏi `frontend/app/(app)/importer/page.tsx` thành `frontend/components/stepper.tsx` (API: `steps: readonly string[]`, `current: string`, `label?`). Importer là nơi DUY NHẤT đang có step indicator; component generic để wizard sau tái dùng.
2. **Bảng mapping (G1) 4 cột** theo yêu cầu owner: CSV column / AI column suggest (key chuẩn hoá mono + ghi chú) / Explain (`entry.reason`, fallback `candidate.description`) / Action dropdown **Approve | Change… | Ignore** (Ignore là bổ sung so với spec 2-option của owner — cần cho AMBIGUOUS, backend 422 nếu approve row ambiguous; Approve bị disable trên row AMBIGUOUS). Change hiện input target_key; lúc submit FE fetch `GET /api/products/{id}/schema` để phân biệt **remap** (key đã có) vs **promote** (field mới, `type: "text"`, label tự humanize). Confirm bị chặn khi còn row Change chưa nhập key.
3. **Quyết định All-TEXT** (owner chọn qua câu hỏi, agent recommend typed+coerce nhưng bị overrule): product field giữ string nguyên trạng trong JSONB `data`, cast ở analysis layer. Entry đầy đủ trong `docs/decisions.md` (2026-10-12). Backend KHÔNG đổi — all-TEXT đã là behavior hiện hành; `occurred_at` giữ DateTime + row error.
4. **api-checklist** — hàng `GET /api/products/{product_id}/schema`: ⬜→✅ + vị trí FE (hard rule #10).

## File đổi

- `frontend/components/stepper.tsx` (mới)
- `frontend/app/(app)/importer/page.tsx` (bảng G1 + dùng Stepper chung)
- `frontend/hooks/use-products.ts` (+`useActiveSchema`)
- `frontend/lib/types.ts` (+`ActiveSchemaResponse`)
- `docs/api-checklist.md`, `docs/decisions.md`

## Verification

- `pnpm typecheck` sạch · `pnpm test` 50/50 · eslint 4 file sạch 0 cảnh báo.
- Dev server log: các trang 200, không lỗi compile. Đã kiểm `curl` mọi route sau khi restart server (fix riêng: Turbopack dev bị mất route registry → 404 toàn bộ, restart `pnpm dev` chữa).

## Mở cho session sau

- Dev server đang chạy trong background của session ZCode (tắt ZCode là dừng) — chạy `pnpm dev` trong `frontend/` khi cần.
- Nợ đã ghi nhận: mọi chart/trend trên product field phải cast string→số/ngày lúc truy vấn (decisions 2026-10-12).
- `middleware.ts` → `proxy.ts` rename (Next 16 deprecation warning) vẫn chưa làm.
