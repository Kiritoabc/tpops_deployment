#!/bin/sh
set -e
cd /app

# Persist DB on volume: mount e.g. -v tpops-data:/data
export DJANGO_SQLITE_PATH="${DJANGO_SQLITE_PATH:-/data/db.sqlite3}"
mkdir -p "$(dirname "$DJANGO_SQLITE_PATH")" 2>/dev/null || true

python manage.py migrate --noinput
python manage.py create_default_superuser

exec "$@"
