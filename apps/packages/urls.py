from rest_framework.routers import DefaultRouter

from .views import PackageArtifactViewSet, PackageReleaseViewSet

router = DefaultRouter()
router.register("releases", PackageReleaseViewSet, basename="package-release")
router.register("artifacts", PackageArtifactViewSet, basename="package-artifact")

urlpatterns = router.urls
