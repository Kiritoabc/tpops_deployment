from rest_framework.routers import DefaultRouter

from .views import DeploymentTaskViewSet

router = DefaultRouter()
router.register(r"tasks", DeploymentTaskViewSet, basename="deployment-task")

urlpatterns = router.urls
