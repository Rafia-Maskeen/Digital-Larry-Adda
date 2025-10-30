# main/management/commands/populate_sample_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group  # 👈 Fixed: Import Group from django.contrib.auth.models
from main.models import Vehicle, Route, VehicleLocation, Seat, CustomUser
from datetime import datetime, timedelta
from django.utils import timezone
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate sample data for testing'

    def handle(self, *args, **options):
        try:
            # Create groups if not exist
            for group_name in ['Passenger', 'Manager', 'Driver']:
                Group.objects.get_or_create(name=group_name)

            # Create sample manager
            manager, created = User.objects.get_or_create(
                username='manager1',
                defaults={
                    'email': 'manager@test.com',
                    'is_active': True
                }
            )
            if created:
                manager.set_password('manager123')
                manager.save()
            manager.groups.add(Group.objects.get(name='Manager'))

            # Create sample driver
            driver, created = User.objects.get_or_create(
                username='driver1',
                defaults={
                    'email': 'driver@test.com',
                    'is_active': True
                }
            )
            if created:
                driver.set_password('driver123')
                driver.save()
            driver.groups.add(Group.objects.get(name='Driver'))

            # Create sample vehicle
            vehicle, _ = Vehicle.objects.get_or_create(
                name='Toyota Hiace',
                number_plate='ABC-123',
                defaults={
                    'manager': manager,
                    'driver': driver,
                    'status': 'Active'
                }
            )

            # Create seats (if not created by signal)
            if not Seat.objects.filter(vehicle=vehicle).exists():
                for i in range(1, 21):
                    Seat.objects.create(
                        vehicle=vehicle,
                        seat_number=str(i),
                        seat_type=random.choice(['VIP', 'STD']),
                        fare=500 if random.choice(['VIP', 'STD']) == 'VIP' else 300,
                        is_available=True
                    )

            # Create sample route
            route, _ = Route.objects.get_or_create(
                start_location='Hostel',
                end_location='Main Campus',
                vehicle=vehicle,
                defaults={
                    'departure_time': datetime.now(tz=timezone.utc) + timedelta(hours=random.randint(1, 5)),
                    'arrival_time': datetime.now(tz=timezone.utc) + timedelta(hours=random.randint(2, 6)),
                    'fare': 400.00
                }
            )

            # Create sample GPS location
            VehicleLocation.objects.update_or_create(
                vehicle=vehicle,
                defaults={
                    'latitude': 33.6844 + random.uniform(-0.01, 0.01),
                    'longitude': 73.0479 + random.uniform(-0.01, 0.01),
                }
            )

            self.stdout.write(self.style.SUCCESS('Sample data populated successfully!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error populating data: {str(e)}'))