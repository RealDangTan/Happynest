# Handoff — 2026-10-12 — ZCode: export toàn bộ diagram mermaid trong docs/architecture ra PNG

## Đã làm

1. Extract **30 khối ```mermaid** từ 9 file `.md` trong `docs/architecture/` (README.md không có block) bằng script Node tạm (không commit).
2. Render từng block ra PNG `@2x` (scale 2, nền trắng) bằng `@mermaid-js/mermaid-cli` (cài tạm trong `%TEMP%/mermaid-export`, dùng Chrome hệ thống qua puppeteer-config — **không** tải Chromium, không đụng repo deps).
3. Đặc biệt: `06-erd-1.png` render lại với `--size 2000` (ERD gốc rất rộng, viewport mặc định làm chữ quá nhỏ) → 4000×3580, chữ sắc nét.

## Kết quả

- `docs/architecture/image-asset/` — 30 PNG, tên `{tên-file}-{số-thứ-tự-block}.png` (VD `01-system-overview-1.png` = block mermaid đầu của `01-system-overview.md`), map 1:1 theo thứ tự xuất hiện trong từng file.
- Đã soát mẫu đủ mọi loại diagram (flowchart LR/TB, sequence, stateDiagram, erDiagram, deployment): tiếng Việt + dấu + emoji render đúng, không block nào fail parse.

## Lưu ý cho session sau

- PNG là render tĩnh tại thời điểm này — sửa mermaid source trong `docs/architecture/*.md` thì phải render lại (script + node_modules còn ở `%TEMP%/mermaid-export/`, chưa đưa vào repo).
- Không file markdown nào bị sửa; chỉ thêm thư mục `image-asset/`.
