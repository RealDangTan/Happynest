import type { NextConfig } from "next"

// Origin của FastAPI cho rewrite /api/*. Local dev mặc định 127.0.0.1:8000;
// khi deploy (Vercel) đặt env `API_PROXY_ORIGIN` = URL backend public
// (tunnel/VPS) — vẫn giữ same-origin qua proxy nên cookie httpOnly không cần
// CORS (delivery-design-spec §2).
const API_PROXY_ORIGIN = process.env.API_PROXY_ORIGIN ?? "http://127.0.0.1:8000"

const nextConfig: NextConfig = {
  // Cho phép next dev nhận request/ws từ tunnel public (ngrok/trycloudflare có
  // domain ngẫu nhiên → wildcard). Không có dòng này, dev server chặn websocket
  // HMR cross-origin → React không hydrate qua link public (FE-14 addendum).
  allowedDevOrigins: ["localhost", "127.0.0.1", "*.trycloudflare.com"],
  // Proxy /api/* về FastAPI giữ same-origin → cookie httpOnly SameSite=Lax
  // hoạt động không cần CORS, backend không đổi (delivery-design-spec §2).
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_PROXY_ORIGIN}/api/:path*`,
      },
    ]
  },
  // Generate actions / agent runs là route LLM đồng bộ (60–120s) — proxy mặc định
  // cắt ở 30s → 500. Nới timeout lên 5 phút (FE-12 verify 2026-09-15).
  experimental: {
    proxyTimeout: 300_000,
  },
}

export default nextConfig
