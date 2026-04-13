# TPOPS 部署平台 — 单镜像（Django + Channels / Daphne）
# 默认 Python 3.10；与 requirements 中 Django 3.2 兼容
FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=tpops_deployment.settings \
    DJANGO_DEBUG=0 \
    DJANGO_ALLOWED_HOSTS=* \
    DJANGO_SQLITE_PATH=/data/db.sqlite3 \
    BOOTSTRAP_SUPERUSER_USERNAME=admin \
    BOOTSTRAP_SUPERUSER_PASSWORD=Gauss_246 \
    BOOTSTRAP_SUPERUSER_EMAIL=admin@localhost

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x docker-entrypoint.sh \
    && mkdir -p /data static

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "tpops_deployment.asgi:application"]
