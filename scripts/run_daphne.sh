#!/usr/bin/env bash
# 在服务器项目根目录旁执行（或通过 SSH 登录后执行），不依赖 PyCharm 远程 Run。
# 用法：
#   chmod +x scripts/run_daphne.sh
#   ./scripts/run_daphne.sh
# 可选环境变量：
#   DJANGO_SECRET_KEY   必填于生产
#   DAPHNE_BIND         默认 0.0.0.0
#   DAPHNE_PORT         默认 8000

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f "venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "venv/bin/activate"
fi

if [[ -z "${DJANGO_SECRET_KEY:-}" ]]; then
  echo "WARN: DJANGO_SECRET_KEY 未设置，使用开发默认值（勿用于生产）" >&2
  export DJANGO_SECRET_KEY="django-insecure-change-me-in-production"
fi

BIND="${DAPHNE_BIND:-0.0.0.0}"
PORT="${DAPHNE_PORT:-8000}"

echo "启动 daphne: $BIND:$PORT  目录: $ROOT" >&2
exec python -m daphne -b "$BIND" -p "$PORT" tpops_deployment.asgi:application
