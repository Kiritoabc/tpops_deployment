from django.urls import re_path

from .consumers import DeploymentConsumer
from .log_tail_consumer import DeployLogTailConsumer

websocket_urlpatterns = [
    re_path(r"ws/deploy/(?P<task_id>\d+)/$", DeploymentConsumer.as_asgi()),
    re_path(
        r"ws/deploy/(?P<task_id>\d+)/log/$",
        DeployLogTailConsumer.as_asgi(),
    ),
]
