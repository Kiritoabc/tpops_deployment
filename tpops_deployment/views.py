"""
SPA 首页：必须按原始 HTML 返回，不能使用 TemplateView，
否则 Django 会把 Vue 的 {{ }} 当成模板语法解析并报错。

本地 ``/static/js/app/*.js`` 等无 hash 文件名，浏览器易长期缓存导致与后端不一致；
在返回 HTML 时为这些 URL 追加 ``?v=<目录内最大 mtime>`` 作为缓存破坏参数。
"""
import re
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse


def _app_static_cache_bust_tag() -> str:
    d = Path(settings.BASE_DIR) / "static/js/app"
    mt = 0
    if d.is_dir():
        for p in d.glob("*.js"):
            try:
                mt = max(mt, int(p.stat().st_mtime))
            except OSError:
                pass
    css = Path(settings.BASE_DIR) / "static/css/app.css"
    try:
        if css.is_file():
            mt = max(mt, int(css.stat().st_mtime))
    except OSError:
        pass
    return str(mt) if mt else "0"


def spa_index(request):
    path = Path(settings.BASE_DIR) / "templates" / "index.html"
    html = path.read_text(encoding="utf-8")
    v = _app_static_cache_bust_tag()
    # 仅给 /static/js/app/*.js 追加 ?v=（CDN 外链不动）
    html = re.sub(
        r'(src=")(/static/js/app/[^"?]+\.js)(")',
        r"\1\2?v=" + v + r"\3",
        html,
    )
    html = html.replace(
        'href="/static/css/app.css"',
        'href="/static/css/app.css?v=%s"' % v,
        1,
    )
    resp = HttpResponse(html, content_type="text/html; charset=utf-8")
    resp["Cache-Control"] = "no-store, max-age=0"
    return resp
