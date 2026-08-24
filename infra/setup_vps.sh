#!/usr/bin/env bash
# setup_vps.sh — placeholder skeleton cho phase DEPLOY (cuối khóa luận).
# Target: Ubuntu native VPS + systemd + Caddy. KHÔNG Docker (bị cấm vĩnh viễn).
# Điền nội dung thật khi đến phase deploy; giữ file này làm mốc cấu trúc.
set -euo pipefail

# TODO(phase-deploy):
#   1. apt install: python3.12, uv, caddy, unzip
#   2. Tạo user hệ thống chạy app (không login shell)
#   3. rsync backend/ + uv sync --frozen
#   4. Copy systemd unit files từ infra/systemd/ -> /etc/systemd/system/
#   5. systemctl enable --now <units>
#   6. Caddy reverse proxy -> 127.0.0.1:<port> + TLS tự động

echo "placeholder — điền ở phase deploy"
