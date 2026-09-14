from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_activity_event(*, project_id: int, payload: dict) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        # No CHANNEL_LAYERS configured (e.g. a management command run
        # without Redis available) — degrade to "no live update" rather
        # than raising, since the ActivityLog row itself is already saved.
        return
    async_to_sync(channel_layer.group_send)(
        f"project_{project_id}",
        {"type": "activity.event", "payload": payload},
    )
