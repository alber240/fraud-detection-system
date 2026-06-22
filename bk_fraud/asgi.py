"""
ASGI config for bk_fraud project.
Used for WebSocket real-time updates with Django Channels.
"""

import os
from django.core.asgi import get_asgi_application

# First, configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bk_fraud.settings')

# Initialize Django ASGI application early
django_asgi_app = get_asgi_application()

# Now import Channel layers after Django is ready
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path, re_path
from prediction import consumers

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter([
                # Make sure the path matches exactly what the client is requesting
                re_path(r'^ws/transactions/$', consumers.TransactionConsumer.as_asgi()),
                re_path(r'^ws/alerts/$', consumers.AlertConsumer.as_asgi()),
            ])
        )
    ),
})