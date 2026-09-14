import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

# get_asgi_application() calls django.setup() internally, populating the
# app registry — it must run before anything below it is imported, since
# routing -> consumers -> models would otherwise raise AppRegistryNotReady.
django_asgi_app = get_asgi_application()

from config.channels_auth import JWTAuthMiddlewareStack  # noqa: E402
from config.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
