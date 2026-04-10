from rest_framework.routers import DefaultRouter

from .views import HostViewSet

router = DefaultRouter()
router.register(r"", HostViewSet, basename="host")

urlpatterns = router.urls
