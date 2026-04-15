from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve

from .views import spa_index

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.tpops_auth.urls")),
    path("api/hosts/", include("apps.hosts.urls")),
    path("api/deployment/", include("apps.deployment.urls")),
    path("api/packages/", include("apps.packages.urls")),
    path("api/manifest/", include("apps.manifest.urls")),
    path("", spa_index, name="spa"),
]

if settings.DEBUG:
    urlpatterns += [
        path(
            "media/<path:path>",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
