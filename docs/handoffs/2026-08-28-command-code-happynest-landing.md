# Handoff: Happynest landing page /landing (pixel-nest direction)
- Date: 2026-08-28
- From: command-code
- To: any
- Branch / worktree: main (shared working tree — voc-os rewrite vẫn đang dở ở tree này, KHÔNG đụng)
- Plan: C:\Users\ADMIN\.commandcode\plans\happynest-landing-page.md (v2, mood board Happynest Style & Art Direction)
- Status: done (page render OK, chưa commit)

## Done
- Trang landing công khai `/landing`: `frontend/app/landing/page.tsx` + `motion.tsx`
  (client: Reveal/CountUp/ConfidenceRing/SignalField/LandingNav/BirdSvg) +
  `landing.css` (toàn bộ style scope dưới `.hn-*`, không đụng globals.css).
- Design theo mood board: palette Deep `#0D0E0A` / Charcoal / Moss / Olive / Ivory /
  Soft Olive / Gold Mist; font Fraunces (display) + Inter (body) + Silkscreen (pixel
  eyebrow) qua next/font. Pixel motif: stepped connectors, nested frames + corner
  ticks, grain/vignette overlay, APPROVED stamp.
- Hero: placeholder có sẵn comment chỉ cách swap — drop ảnh AI-generated vào
  `frontend/public/landing/hero.png` rồi thay `<HeroPlaceholder/>` bằng `<Image>`.
- Motion: load stagger, SignalField dot drift, scroll Reveal (IntersectionObserver,
  fire-once), stepped-line draw, marquee 2 chiều có pause-on-hover + chip "classify"
  nhấp nháy đổi tag, count-up stats, hover micro (cluster converge, evidence dot
  travel, checkbox tick, stamp, bird blink, lantern flicker), flying bird ở final CTA.
  `prefers-reduced-motion`: tắt toàn bộ, content luôn hiện đủ.
- Middleware: thêm `/landing` vào `PUBLIC_PATHS` (`frontend/middleware.ts`) — bắt buộc
  vì middleware mặc định redirect mọi route chưa login về /login.

## Evidence
- `npm run typecheck` sạch.
- Dev server: `GET /landing` → 200; render chứa đủ mọi section (hero placeholder,
  pipeline 5 bước, marquee, features, proof, final CTA, footer); không có error marker.
- LƯU Ý: trước khi verify có một dev server CŨ (PID 31032) chiếm :3000 không
  hot-reload middleware → đã kill và thay bằng instance mới. Instance hiện tại do
  agent khởi động, vẫn đang chạy ở :3000.

## Blocked / risks
- Chưa screenshot visual QA (mobile 375px / reduced-motion) — phần verify bằng mắt
  để lại cho owner hoặc phiên sau với agent-browser.
- Chưa commit (tree đang dở của voc-os rewrite — commit pathspec riêng nếu commit).

## Next steps
1. Owner generate hero image → drop vào `public/landing/hero.png` + swap
   `<HeroPlaceholder/>` (comment hướng dẫn ngay trong page.tsx).
2. Visual QA mobile + reduced-motion.
3. CTA hiện tại là `href="#"` — nối vào auth flow khi có onboarding thật.

## Update (2026-08-29): global routing + 404
- `frontend/middleware.ts` viết lại theo chỉ đạo owner: logged-in (cookie
  access_token) + url bất kỳ trong {/, /login, /register, /landing} → /dashboard;
  anonymous + route không công khai → /landing (không còn anonymous → /login).
  PUBLIC_PATHS = ["/login", "/register", "/landing"]. Chi tiết:
  docs/decisions.md entry 2026-08-28 (supersede một phần OQ-3).
- `app/not-found.tsx` mới: trang 404 theo mood board (Silkscreen "404" gold,
  bird-in-nest, SignalField drift, grain/vignette, CTA "Back to the nest" → "/"
  để middleware tự điều hướng theo session). Fonts tách ra
  `app/landing/fonts.ts` dùng chung cho landing + 404.
- LỖI ĐÃ GỠ: `.next/dev/types/routes.d.ts` bị corrupt (chứa markdown) khiến
  `next build` fail typecheck VÀ dev server 404 toàn bộ route — xoá `.next`,
  build xanh lại 13 route. Nếu gặp lại: xoá `.next` trước khi debug code.
- LƯU Ý Next 16: file convention `middleware.ts` deprecated → khuyến nghị đổi
  tên thành `proxy.ts` (vẫn hoạt động, chỉ warning). Chưa đổi — việc nhỏ, kèm
  phiên dọn FE sau.
- Verify matrix (curl, dev server chạy tại :3000): anon / → /landing,
  anon /feedbacks → /landing, anon /login 200, anon /landing 200, auth / →
  /dashboard, auth /landing → /dashboard, auth /login → /dashboard,
  auth /dashboard 200, auth /does-not-exist → 404 moodboard.
