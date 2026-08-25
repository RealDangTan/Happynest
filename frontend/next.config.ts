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
}

export default nextConfig
