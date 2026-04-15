#!/usr/bin/env bash
# 远程调试：在服务器上启动 daphne，并等待 PyCharm 通过 debugpy 附加。
#
# 1) 远程 venv 安装 debugpy：
#    pip install -r requirements-dev.txt
# 2) 本机开一个 SSH 转发（把远程 5678 映到本机，便于 PyCharm 附加）：
#    ssh -N -L 5678:127.0.0.1:5678 用户@远程主机
# 3) 另一个 SSH 会话在服务器执行本脚本（默认只监听 127.0.0.1，更安全）：
#    cd /data/tpops_deployment && ./scripts/run_daphne_debugpy.sh
# 4) PyCharm：Run → Attach to Process… → 选 Python / Using Debugpy → Host 127.0.0.1 Port 5678
#
# 环境变量：
#   DJANGO_SECRET_KEY
#   DEBUGPY_HOST   默认 127.0.0.1（配合 SSH -L）；若内网直连可改为 0.0.0.0
#   DEBUGPY_PORT   默认 5678
#   DAPHNE_BIND    默认 0.0.0.0
#   DAPHNE_PORT    默认 8000

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f "venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "venv/bin/activate"
fi

if ! python -c "import debugpy" 2>/dev/null; then
  echo "未安装 debugpy。远程执行: pip install debugpy 或 pip install -r requirements-dev.txt" >&2
  exit 1
fi

if [[ -z "${DJANGO_SECRET_KEY:-}" ]]; then
  export DJANGO_SECRET_KEY="django-insecure-change-me-in-production"
  echo "WARN: 使用默认 DJANGO_SECRET_KEY" >&2
fi

DEBUGPY_HOST="${DEBUGPY_HOST:-127.0.0.1}"
DEBUGPY_PORT="${DEBUGPY_PORT:-5678}"
DAPHNE_BIND="${DAPHNE_BIND:-0.0.0.0}"
DAPHNE_PORT="${DAPHNE_PORT:-8000}"

echo "debugpy 监听 ${DEBUGPY_HOST}:${DEBUGPY_PORT}，附加后再继续启动 daphne ${DAPHNE_BIND}:${DAPHNE_PORT}" >&2
echo "若在本机 PyCharm 附加：请先 ssh -L ${DEBUGPY_PORT}:127.0.0.1:${DEBUGPY_PORT} 用户@本脚本所在主机" >&2

exec python -m debugpy --listen "${DEBUGPY_HOST}:${DEBUGPY_PORT}" --wait-for-client -m daphne \
  -b "${DAPHNE_BIND}" -p "${DAPHNE_PORT}" tpops_deployment.asgi:application
