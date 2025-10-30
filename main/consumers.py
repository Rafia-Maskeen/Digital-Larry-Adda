# 👈 NEW: Create main/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import VehicleLocation

class VehicleLocationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add('vehicle_locations', self.channel_name)
        await self.accept()
        # Send initial data
        await self.send_initial_data()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('vehicle_locations', self.channel_name)

    async def send_initial_data(self):
        locations = await self.get_locations()
        await self.send(text_data=json.dumps({
            'type': 'location_update',
            'locations': locations
        }))

    @database_sync_to_async
    def get_locations(self):
        locations = VehicleLocation.objects.all()
        return [{"id": loc.vehicle.id, "lat": loc.latitude, "lng": loc.longitude} for loc in locations]

    async def location_update(self, event):
        await self.send(text_data=json.dumps(event['locations']))