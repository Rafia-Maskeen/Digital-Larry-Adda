from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Vehicle, Seat, AIInteraction , Booking # 👈 NEW: For logging
import random
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import Group

@receiver(post_save, sender=Vehicle)
def create_seats_for_vehicle(sender, instance, created, **kwargs):
    if created:
        seat_types = ['VIP', 'STD']
        for seat_number in range(1, 21):  # Assume 20 seats per vehicle for example
            Seat.objects.create(
                vehicle=instance,
                seat_number=str(seat_number),
                seat_type=random.choice(seat_types),
                fare=500 if random.choice(seat_types) == 'VIP' else 300
            )

# 👈 NEW: Email notification on vehicle breakdown
@receiver(post_save, sender=Vehicle)
def notify_passengers_on_breakdown(sender, instance, **kwargs):
    if instance.status == 'Broken' and kwargs.get('update_fields', {}).get('status'):  # Only on status change
        # Find affected bookings
        affected_bookings = Booking.objects.filter(route__vehicle=instance, status='Confirmed')
        for booking in affected_bookings:
            send_mail(
                'Vehicle Breakdown Alert',
                f'Dear {booking.user.username}, the vehicle {instance.name} ({instance.number_plate}) for your route has broken down. Please check alternatives or contact support.',
                settings.EMAIL_HOST_USER,
                [booking.user.email],
                fail_silently=False,
            )

# 👈 NEW: Simulate GPS updates (run via cron or management command for real GPS)
@receiver(post_save, sender=Vehicle)
def simulate_gps_update(sender, instance, created, **kwargs):
    if created or random.random() < 0.1:  # 10% chance on save (simulate periodic update)
        from .models import VehicleLocation
        VehicleLocation.objects.update_or_create(
            vehicle=instance,
            defaults={
                'latitude': random.uniform(33.6, 33.7),  # Random lat around Pakistan
                'longitude': random.uniform(73.0, 73.1),  # Random lng
            }
        )

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def assign_driver_group(sender, instance, created, **kwargs):
    if not created:
        return

    # If user was created from admin (no request context), auto set Driver
    if instance.is_staff:  
        try:
            driver_group = Group.objects.get(name="Driver")
            instance.groups.add(driver_group)
        except Group.DoesNotExist:
            pass