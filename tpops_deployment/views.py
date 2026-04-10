"""
SPA 首页：必须按原始 HTML 返回，不能使用 TemplateView，
否则 Django 会把 Vue 的 {{ }} 当成模板语法解析并报错。
"""
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse


def spa_index(request):
    path = Path(settings.BASE_DIR) / "templates" / "index.html"
    html = path.read_text(encoding="utf-8")
    return HttpResponse(html, content_type="text/html; charset=utf-8")
