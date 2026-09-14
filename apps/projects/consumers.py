from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import ProjectMembership


class ProjectConsumer(AsyncJsonWebsocketConsumer):
    """One group per project (`project_<id>`); relays activity events
    (task created/assigned/status-changed, comments, membership and
    workflow changes — everything apps.activity already logs) to every
    connected member of that project.

    Membership is re-checked at connect time the same way every REST
    endpoint checks it — a WebSocket is just another way to read data, and
    Phase 5's "never trust the frontend" rule applies here too.
    """

    async def connect(self):
        self.project_id = self.scope["url_route"]["kwargs"]["project_id"]
        user = self.scope["user"]
        if not user.is_authenticated or not await self._is_project_member(user, self.project_id):
            await self.close(code=4403)
            return
        self.group_name = f"project_{self.project_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    @staticmethod
    @database_sync_to_async
    def _is_project_member(user, project_id) -> bool:
        return ProjectMembership.objects.filter(project_id=project_id, user=user).exists()

    async def activity_event(self, event):
        await self.send_json(event["payload"])
