import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  // Proxy /api/* về FastAPI giữ same-origin → cookie httpOnly SameSite=Lax
  // hoạt động không cần CORS, backend không đổi (delivery-design-spec §2).
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
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
