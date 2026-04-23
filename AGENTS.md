# Agent / contributor guide

This file orients automated agents and humans who edit **TPOPS 白屏化部署工具**: a Django + DRF + Channels backend with a **Vue 3 + Element Plus (CDN)** single-page UI served from `templates/index.html`.

For full architecture and data flow, read **`docs/PROJECT_GUIDE.md`** first. **`README.md`** covers setup, env vars, remote `appctl.sh` commands, and `user_edit_file.conf` behavior. For **per-module, beginner-friendly** chapters (DB, each app, URLs, WS, frontend), see **`docs/chapters/README.md`** and the index **`docs/PLATFORM_REFERENCE.md`**.

## Tech stack

- **Python**: target **3.7.9** in production → **Django 3.2 LTS** (see `requirements.txt`).
- **API**: Django REST Framework + SimpleJWT.
- **Realtime**: Django Channels + **Daphne** (ASGI); default in-memory channel layer.
- **SSH / files**: Paramiko; host secrets encrypted with Fernet (`apps/hosts/crypto.py`).
- **YAML**: PyYAML for remote `manifest.yaml` parsing (`apps/manifest/parser.py`).

## Repository map

| Area | Location |
|------|----------|
| Django project | `tpops_deployment/` (`settings.py`, `urls.py`, `asgi.py`, `views.py` for SPA) |
| Auth (custom user, JWT) | `apps/tpops_auth/` |
| Hosts + SSH | `apps/hosts/` |
| Deployment tasks + runner | `apps/deployment/` — **`runner.py`** is the main execution pipeline |
| Manifest HTTP / parsing | `apps/manifest/` |
| Packages (releases, uploads) | `apps/packages/` |
| WebSocket consumers | `apps/logs/` |
| Frontend SPA | `templates/index.html` (inline Vue; avoid syntax unsupported by older browsers) |
| Feature plans | `plan/` — new work should start with **`plan/plan-<topic>.md`** per `plan/README.md` |

## Local run (minimal)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_SECRET_KEY='change-me'
python3 manage.py migrate
python3 manage.py createsuperuser
daphne -b 0.0.0.0 -p 8000 tpops_deployment.asgi:application
```

Use **`daphne`** (not only `runserver`) when exercising WebSockets reliably. After pulling code or switching environments, run **`migrate`** before relying on tasks or APIs.

## Conventions agents should follow

1. **Read before changing**: trace HTTP → `DeploymentTaskViewSet` → `apps/deployment/runner.py` for task behavior; WebSocket auth uses **JWT in the query string** (browsers cannot set WS headers).
2. **Threading + DB**: background task code must continue calling **`close_old_connections()`** where the codebase already does; SQLite is sensitive to locks and stale connections.
3. **Scope**: match existing style; avoid drive-by refactors and unrelated files. The SPA is one large HTML file — keep UI changes cohesive with existing CSS variables and layout patterns.
4. **Security**: never commit real `DJANGO_SECRET_KEY`, host passwords, or private keys. SSH credentials are encrypted at rest; do not log decrypted secrets.
5. **Paths in docs and comments**: prefer **relative** paths from the repo root (e.g. `apps/deployment/runner.py`).
6. **Production notes** (from project docs): prefer PostgreSQL/MySQL over SQLite for serious use; replace **InMemoryChannelLayer** with Redis (or similar) for multi-process deployments.

## Quick “where do I change X?”

| Goal | Start here |
|------|------------|
| Task lifecycle, appctl, manifest polling, WS payloads | `apps/deployment/runner.py`, `apps/deployment/views.py` |
| SSH commands, SFTP, remote paths | `apps/hosts/ssh_client.py` |
| Manifest tree / merge rules | `apps/manifest/parser.py` |
| WS protocol / tail logs | `apps/logs/` |
| REST routes | `tpops_deployment/urls.py` and per-app `urls.py` |
| UI behavior | `templates/index.html` |

## Tests and lint

There is no centralized pytest/ruff config in this repo today. If you add automated checks, document the exact commands in **`README.md`** or here so agents can run them consistently.
