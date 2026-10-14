# Handoff — 2026-10-12 — zcode — Chat dock "night nest" surface

## Context (vào)

Owner yêu cầu sửa nền chatbot trong dock trái: panel chat đang dùng token light
(`bg-background` Field Paper) dán vào aside Pine Ink tối → lệch hẳn, không giống
chatbot. Yêu cầu: nền tối, đảo màu text/component bên trong, dùng đúng bộ UI kit
shadcn sẵn có, chú ý tương phản. (FE skill `frontend-design` đã load trước khi code.)

## What changed

1. **`frontend/app/globals.css`** — thêm class `.chat-night`: remap TOÀN BỘ token
   set cho một subtree (cùng cơ chế với `.dark`), brand-pinned:
   - `--background/--foreground` → Pine Ink `#14251d` / `#eef1e4` (khớp sidebar,
     panel liền một surface tối).
   - `--primary` ĐẢO thành giấy `#fcfcf8` (+ `--primary-foreground` pine) →
     user bubble (Bubble variant default) và nút gửi trở thành "tờ giấy trên tổ tối".
   - `--card/--popover` → `#22352b` (sidebar-accent elevation), `--muted` →
     `#2b3e32`, `--secondary/--accent/--border/--input` → `#33463a`.
   - `--muted-foreground` → `#a9b6a4` (sage sáng cho text phụ trên nền tối).
   - `--destructive` → `#e28573` (brick sáng lại cho AA trên dark),
     `--signal` → `#8ab4d6` (Signal Blue nâng độ sáng, chỉ trong subtree),
     `--ring` → lichen.
2. **`frontend/components/shell/chat-thread.tsx`** — root div thêm class
   `chat-night`; composer InputGroup thêm `bg-muted/50` (khung composer "đặc"
   giống chatbot reference); cập nhật doc comment. Không đổi bất kỳ màu tay nào
   trong component — mọi màu vẫn qua semantic tokens.
3. **`frontend/components/ai/ai-trace.tsx`** — dòng error trace
   `text-destructive/80` → `text-destructive` (3.5:1 → 4.86:1 trên dark card;
   trên /data-graph light vẫn ~7:1). Component dùng chung data-graph nên KHÔNG
   bị style dark cứng — remap token chỉ có tác dụng trong subtree `.chat-night`.

## Kết quả verify (số liệu, WCAG)

Typecheck ✅ · eslint (2 file tsx) ✅ · vitest 50/50 ✅.
Audit computed-style trên tab /vault đang mở (IAB screenshot pipeline lỗi
"activity capture failed for guest" nên verify bằng số liệu thay vì ảnh):

| Element | Màu | Contrast |
|---|---|---|
| Surface chat | `#14251d` / `#eef1e4` | **13.98:1** |
| Send button + user bubble (primary đảo) | `#fcfcf8` / `#14251d` | **15.56:1** |
| Chip gợi ý | `#22352b` / `#eef1e4` | **11.37:1** |
| Muted text trên card | `#a9b6a4` / `#22352b` | **6.15:1** |
| Destructive trên card | `#e28573` / `#22352b` | **4.86:1** |
| Signal token trong scope | `#8ab4d6` | ~5.9:1 trên card |

## Ghi chú cho agent sau

- Dropdown "Recent investigations" là Radix portal → thoát `.chat-night`, vẫn
  light (popover nổi trên nền tối — pattern chuẩn, chủ động giữ nguyên).
- `.dark` (block hiện có) KHÔNG dùng cho panel vì giá trị generic không khớp
  brand Pine Ink; `.chat-night` là remap brand-pinned riêng cho chat dock.
- Home tab giữ nguyên sidebar tokens — chỉ chat tab là night surface.
- Nếu sau này muốn panel dark trên cả data-graph (AiTrace), nhân cách dùng
  `.chat-night` thay vì hard-code màu trong component.
