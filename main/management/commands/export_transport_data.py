# your_app/management/commands/export_transport_data.py
import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import Vehicle, Route, Seat

class Command(BaseCommand):
    help = 'Export transport data to a JSON file'

    def handle(self, *args, **kwargs):
        # Fetch data
        routes = Route.objects.select_related('vehicle').filter(
            departure_time__gt=timezone.now()
        ).order_by('departure_time')
        
        data = {
            'vehicles': [],
            'routes': [],
        }

        # Collect vehicle data
        for vehicle in Vehicle.objects.all():
            available_seats = Seat.objects.filter(
                vehicle=vehicle, is_available=True
            ).count()
            data['vehicles'].append({
                'id': vehicle.id,
                'name': vehicle.name,
                'available_seats': available_seats,
            })

        # Collect route data
        for route in routes:
            available_seats = Seat.objects.filter(
                vehicle=route.vehicle, is_available=True
            ).count()
            data['routes'].append({
                'id': route.id,
                'start_location': route.start_location,
                'end_location': route.end_location,
                'departure_time': str(route.departure_time),
                'arrival_time': str(route.arrival_time),
                'vehicle_name': route.vehicle.name,
                'available_seats': available_seats,
                'vip_seats': route.vip_seats,
                'std_seats': route.std_seats,
            })

        # Save to JSON file
        with open('transport_data.json', 'w') as f:
            json.dump(data, f, indent=2)

        self.stdout.write(self.style.SUCCESS('Successfully exported transport data to transport_data.json'))