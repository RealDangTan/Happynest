# happynest-web — Frontend Happynest

Next.js (App Router) + shadcn/ui preset `b4IdeDqtkJ` (vega style, radix base, olive theme).

## Chạy

```bash
pnpm install   # yêu cầu Node ≥ 20.18.1 (đã chạy trên v24)
pnpm dev       # http://localhost:3000
```

Cần backend FastAPI chạy tại `http://127.0.0.1:8000` trước (xem `../AGENTS.md`):

```bash
cd ../backend && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Kiến trúc proxy

Mọi request `/api/*` từ browser được Next.js rewrite về `http://127.0.0.1:8000/api/*`
(xem `next.config.ts`). Nhờ đó origin duy nhất là `:3000`, cookie JWT `access_token`
httpOnly SameSite=Lax do FastAPI set hoạt động không cần CORS — backend không đổi gì.

## Kiểm thử

```bash
pnpm test        # vitest run (unit: lib/api.ts)
pnpm build       # kiểm tra production build + TypeScript
```

## Tài liệu

- Spec thiết kế: [`../docs/plans/delivery-design-spec.md`](../docs/plans/delivery-design-spec.md)
- API contract (C1–C6): [`../docs/plans/delivery-contracts.md`](../docs/plans/delivery-contracts.md)
- Ghi chú API hiện có: [`../docs/api-notes.md`](../docs/api-notes.md)
- Roadmap thực thi: [`../docs/plans/delivery-execute-plan.md`](../docs/plans/delivery-execute-plan.md)
