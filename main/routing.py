# 👈 NEW: Create main/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/vehicle_locations/$', consumers.VehicleLocationConsumer.as_asgi()),
]