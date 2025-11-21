import os
import sys
from pathlib import Path

# Add project root to Python path for shared module access
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import dashboard.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuxsec.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                dashboard.routing.websocket_urlpatterns
            )
        )
    ),
})