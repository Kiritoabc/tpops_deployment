import os

# 必须在导入任何会访问 django.conf.settings 的模块（如 simplejwt）之前配置 Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tpops_deployment.settings")

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

# 在 Django 初始化后再导入 consumers / simplejwt
from apps.logs.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
