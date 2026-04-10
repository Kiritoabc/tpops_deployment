from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.tpops_auth.urls")),
    path("api/hosts/", include("apps.hosts.urls")),
    path("api/deployment/", include("apps.deployment.urls")),
    path("api/manifest/", include("apps.manifest.urls")),
    path(
        "",
        TemplateView.as_view(template_name="index.html"),
        name="spa",
    ),
]
