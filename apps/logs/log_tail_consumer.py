import json
import threading
from urllib.parse import parse_qs

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from apps.deployment.access import get_deployment_task_for_user
from apps.deployment.remote_logs import remote_deploy_log_file, remote_log_path, tail_remote_log_chunk
from apps.hosts.serializers import host_ssh_secret
from apps.deployment.user_edit import parse_user_edit_block

User = get_user_model()


@database_sync_to_async
def get_task_deploy(task_id: int, user):
    return get_deployment_task_for_user(task_id, user, select_related=("host",))


class DeployLogTailConsumer(AsyncWebsocketConsumer):
    """
    ?token=&kind=precheck|install  或  &rel=deploy 目录下文件名（仅字母数字._-）
    """

    async def connect(self):
        self.task_id = int(self.scope["url_route"]["kwargs"]["task_id"])
        query = parse_qs(self.scope.get("query_string", b"").decode())
        token = (query.get("token") or [""])[0]
        self.log_kind = (query.get("kind") or ["precheck"])[0]
        if self.log_kind not in ("precheck", "install", "uninstall"):
            self.log_kind = "precheck"
        self.rel_file = (query.get("rel") or [""])[0].strip() or None

        if not token:
            await self.close(code=4401)
            return
        try:
            access = AccessToken(token)
            user = await database_sync_to_async(User.objects.get)(pk=access["user_id"])
        except (TokenError, User.DoesNotExist, KeyError):
            await self.close(code=4401)
            return

        task = await get_task_deploy(self.task_id, user)
        if not task:
            await self.close(code=4403)
            return

        self.task = task
        self._stop = threading.Event()
        self._offset = 0

        await self.accept()
        await self.send(
            text_data=json.dumps(
                {
                    "type": "hello",
                    "task_id": self.task_id,
                    "kind": self.log_kind,
                    "rel": self.rel_file,
                },
                ensure_ascii=False,
            )
        )

        self._thread = threading.Thread(target=self._tail_loop, daemon=True)
        self._thread.start()

    def _tail_loop(self):
        send = async_to_sync(self.send)
        h = self.task.host
        secret = host_ssh_secret(h)
        if not secret:
            send(
                text_data=json.dumps(
                    {"type": "error", "message": "无 SSH 凭证"}, ensure_ascii=False
                )
            )
            return
        kv, err = parse_user_edit_block(self.task.user_edit_content or "")
        if err or not kv.get("log_path"):
            send(
                text_data=json.dumps(
                    {"type": "error", "message": "无法解析 log_path"}, ensure_ascii=False
                )
            )
            return
        lp = kv.get("log_path", "")
        if self.rel_file:
            rpath = remote_deploy_log_file(lp, self.rel_file)
        else:
            rpath = remote_log_path(lp, self.log_kind)
        if not rpath:
            send(
                text_data=json.dumps(
                    {"type": "error", "message": "log_path 为空"}, ensure_ascii=False
                )
            )
            return
        send(
            text_data=json.dumps(
                {"type": "meta", "path": rpath, "kind": self.log_kind},
                ensure_ascii=False,
            )
        )
        off = 0
        missing_count = 0
        while not self._stop.is_set():
            try:
                chunk, new_off, missing = tail_remote_log_chunk(
                    h.hostname,
                    h.port,
                    h.username,
                    h.auth_method,
                    secret,
                    rpath,
                    off,
                )
                off = new_off
                if chunk:
                    send(
                        text_data=json.dumps(
                            {"type": "chunk", "data": chunk}, ensure_ascii=False
                        )
                    )
                if missing:
                    missing_count += 1
                    if missing_count > 30:
                        send(
                            text_data=json.dumps(
                                {"type": "wait", "message": "日志文件尚未创建…"},
                                ensure_ascii=False,
                            )
                        )
                        missing_count = 0
                else:
                    missing_count = 0
            except Exception as exc:
                send(
                    text_data=json.dumps(
                        {"type": "error", "message": str(exc)}, ensure_ascii=False
                    )
                )
            if self._stop.wait(0.4):
                break

    async def disconnect(self, close_code):
        self._stop.set()
