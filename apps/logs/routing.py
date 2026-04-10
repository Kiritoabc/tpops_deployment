from django.urls import re_path

from .consumers import DeploymentConsumer

websocket_urlpatterns = [
    re_path(r"ws/deploy/(?P<task_id>\d+)/$", DeploymentConsumer.as_asgi()),
]
