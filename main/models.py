from django.contrib.auth.models import AbstractUser,User
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.username

class Vehicle(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Broken', 'Broken'),
    ]
    name = models.CharField(max_length=100)
    number_plate = models.CharField(max_length=20, unique=True)
    driver = models.ForeignKey(
        CustomUser, related_name="driver_vehicles",
        on_delete=models.SET_NULL, null=True
    )
    manager = models.ForeignKey(
        CustomUser, related_name="manager_vehicles",
        on_delete=models.SET_NULL, null=True
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')

    def __str__(self):
        return f"{self.name} ({self.number_plate})"

class VehicleLocation(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.vehicle} - ({self.latitude}, {self.longitude})"



class Seat(models.Model):
    SEAT_TYPE_CHOICES = [
        ('VIP', 'VIP'),
        ('STD', 'Standard'),
    ]
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    seat_number = models.CharField(max_length=10)
    seat_type = models.CharField(max_length=3, choices=SEAT_TYPE_CHOICES)
    fare = models.DecimalField(max_digits=8, decimal_places=2)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.seat_number} - {self.get_seat_type_display()} (Rs. {self.fare})"

class Route(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    manager = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='managed_routes')
    start_location = models.CharField(max_length=100)
    end_location = models.CharField(max_length=100)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    fare = models.DecimalField(max_digits=10, decimal_places=2)
    vip_seats = models.PositiveIntegerField(default=0)
    std_seats = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='route_images/', null=True, blank=True)

    def __str__(self):
        return f"{self.start_location} to {self.end_location}"

class Booking(models.Model):
    STATUS_CHOICES = [
        ('Confirmed', 'Confirmed'),
        ('Pending', 'Pending'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    seats = models.ManyToManyField(Seat)  # ⬅ MULTIPLE SEATS
    fare = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"Booking by {self.user} - {self.status}"


class Feedback(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE, null=True, blank=True)  # ✅ allow null
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rate from 1 (poor) to 5 (excellent)"
    )
    comment = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback by {self.user} for {self.route or 'General'} - Rating: {self.rating}"


class Issue(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, null=True, blank=True)
    route = models.ForeignKey(Route, on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(max_length=1000)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Issue by {self.user} - {self.status}"
    
# 👈 NEW: Add this to the end of models.py
class AIInteraction(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)  # Optional if anonymous
    question = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Query by {self.user or 'Anonymous'}: {self.question[:50]}..."

    class Meta:
        ordering = ['-created_at']

from django.conf import settings

class AdminMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} → Admin: {self.subject}"
