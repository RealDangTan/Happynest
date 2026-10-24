# Handoff: Manual taxonomy CRUD — human tự tay xây/sửa/xóa node trên /taxonomy
- Date: 2026-10-23 (session khuya)
- From: zcode
- To: any
- Branch / worktree: codex/activity-center (KHÔNG commit — working tree dùng chung, nhiều WIP khác nằm lộn xộn)
- Milestone: Delivery — taxonomy governance mở rộng (owner directive 2026-10-23)
- Status: done

## Done
- BE `taxonomy_service.py`: `create_manual_node` / `update_manual_node` / `delete_manual_node` + 2 exception (`TaxonomyValidationError`→422, `TaxonomyConflictError`→409). Slug sinh theo plan 31 (cha.con, hậu tố _2/_3); create/delete bump `taxonomy_version`, rename KHÔNG bump (tập nhãn không đổi); xóa chỉ node lá (còn con → 409); dữ liệu `ai_analysis.topics` cũ không bị đụng.
- BE `routes/taxonomies.py`: `POST /api/taxonomies/nodes`, `PATCH /api/taxonomies/nodes/{slug}`, `DELETE /api/taxonomies/nodes/{slug}?product_id=` — tất cả `product_or_404` (isolation) + `log_decision` (action `manual_create/manual_update/manual_delete`, reviewer attribution).
- Schemas `TaxonomyNodeCreateIn` / `TaxonomyNodeUpdateIn`.
- FE `hooks/use-taxonomy.ts`: `useCreateTaxonomyNode` / `useUpdateTaxonomyNode` / `useDeleteTaxonomyNode` (invalidate taxonomy + products).
- FE `app/(app)/taxonomy/page.tsx` (đã load skill shadcn trước khi code UI): nút "Thêm chủ đề" trong CardAction → Dialog (tên + Select cha + Textarea mô tả); TaxonomyRow mới có nút Pencil/Trash hiện trên hover (icon-xs ghost, aria-label tiếng Việt); dialog sửa tên/mô tả (slug hiển thị, note bất biến); AlertDialog xác nhận xóa (giải thích feedback cũ giữ nhãn, còn con phải xóa trước). Follow rule shadcn: FieldGroup+Field, data-icon, gap-*, cn(), SelectGroup bọc SelectItem.
- Docs: `docs/api-checklist.md` thêm 3 row; `docs/decisions.md` entry 2026-10-23.

## Evidence
- `uv run pytest tests/test_taxonomy_crud.py -m integration` → **6 passed** (slug cha.con + bump version, 409 trùng tên, 422 parent lạ, rename giữ slug + không bump, delete 409 khi còn con rồi 204, isolation 404 cho product của account khác).
- FE: `pnpm exec tsc --noEmit` sạch; eslint 2 file đổi → 0 error; `pnpm exec vitest run` → 53 passed.
- Backend đang chạy lại với code mới (`/api/health` ok).

## Not done / gaps
- Chưa có MOVE node (đổi parent của node hiện có) — slug bất biến khiến reparent để lại slug lệch cây; nếu cần sẽ làm endpoint riêng với cảnh báo slug giữ nguyên.
- Xóa node không cascade `ai_analysis` cũ (by design); hợp nhất hàng loạt vẫn qua generate/apply hoặc merge theme.
- FE chưa có test riêng cho 3 dialog (chỉ tsc/eslint/vitest suite cũ); follow-up nhỏ nếu cần.

## Next steps
1. Owner thử trên http://localhost:3000/taxonomy: Thêm chủ đề → chạy lại Analysis → thấy nhãn mới trong enrich.
2. Nếu muốn "đổi tên có đổi cả slug" cho nhãn còn sạch dữ liệu: đề xuất endpoint `rekey` riêng (rename slug + migrate `ai_analysis.topics` trong 1 transaction) — cần decision entry trước khi làm.
