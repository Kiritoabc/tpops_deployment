import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from apps.deployment.access import get_deployment_task_for_user

User = get_user_model()


@database_sync_to_async
def get_task_for_user(task_id: int, user):
    return get_deployment_task_for_user(task_id, user, select_related=("host",))


class DeploymentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.task_id = int(self.scope["url_route"]["kwargs"]["task_id"])
        query = parse_qs(self.scope.get("query_string", b"").decode())
        token = (query.get("token") or [""])[0]
        if not token:
            await self.close(code=4401)
            return
        try:
            access = AccessToken(token)
            user = await database_sync_to_async(User.objects.get)(pk=access["user_id"])
        except (TokenError, User.DoesNotExist, KeyError):
            await self.close(code=4401)
            return

        task = await get_task_for_user(self.task_id, user)
        if not task:
            await self.close(code=4403)
            return

        self.user = user
        self.group_name = "deployment_%s" % self.task_id
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(
            text_data=json.dumps(
                {
                    "type": "hello",
                    "task_id": self.task_id,
                    "status": task.status,
                    "action": task.action,
                    "exit_code": task.exit_code,
                    "error_message": (task.error_message or "")[:2000],
                    "finished_at": task.finished_at.isoformat()
                    if task.finished_at
                    else None,
                    "started_at": task.started_at.isoformat()
                    if task.started_at
                    else None,
                },
                ensure_ascii=False,
            )
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def deployment_event(self, event):
        await self.send(
            text_data=json.dumps(event.get("payload", {}), ensure_ascii=False)
        )
