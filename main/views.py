import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.db.models import Count, Q
from django.http import JsonResponse
from datetime import timedelta
from django.utils import timezone
import openai
import json
from .assistant_engine import handle_transport_query
from django.conf import settings
from .models import AIInteraction, Vehicle, Route, Seat, Booking, Feedback, Issue, VehicleLocation
from .forms import CustomLoginForm, CustomRegisterForm, BookingForm,  VehicleForm, RouteForm

def home(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')

def find_ride(request):
    return render(request, 'find_ride.html')

def vehicles(request):
    vehicles = Vehicle.objects.all()
    return render(request, 'vehicles_list.html', {'vehicles': vehicles})

def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    routes = Route.objects.filter(vehicle=vehicle).order_by('departure_time')
    empty_seats = Seat.objects.filter(vehicle=vehicle, is_available=True).count()
    expected_time = timedelta(hours=1)
    return render(request, 'vehicle_detail.html', {
        'vehicle': vehicle,
        'routes': routes,
        'empty_seats': empty_seats,
        'expected_time': expected_time
    })

def available_vehicles(request):
    pickup = request.GET.get('pickup')
    dropoff = request.GET.get('dropoff')
    routes = Route.objects.filter(start_location__icontains=pickup, end_location__icontains=dropoff)
    return render(request, 'available_vehicles.html', {'routes': routes, 'pickup': pickup, 'dropoff': dropoff})

@login_required
def book_route(request, route_id):
    route = get_object_or_404(Route, id=route_id)
    if request.method == 'POST':
        form = BookingForm(request.POST, route=route)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.route = route
            booking.save()
            booking.seat.is_available = False
            booking.seat.save()
            # Update Route seat counts
            if booking.seat.seat_type == 'VIP':
                route.vip_seats = max(0, route.vip_seats - 1)
            else:
                route.std_seats = max(0, route.std_seats - 1)
            route.save()
            messages.success(request, "Your booking is confirmed!")
            return redirect('booking_success')
    else:
        form = BookingForm(route=route)
    return render(request, 'book_route.html', {'form': form, 'route': route})

@login_required
def booking_success(request):
    return render(request, 'booking_success.html')

def register_view(request):
    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            try:
                passenger_group = Group.objects.get(name='Passenger')
                user.groups.add(passenger_group)
            except Group.DoesNotExist:
                pass
            messages.success(request, 'Account created successfully. Please log in.')
            return redirect('login')
    else:
        form = CustomRegisterForm()
    return render(request, 'register.html', {'form': form})

class CustomLoginView(LoginView):
    form_class = CustomLoginForm
    template_name = 'login.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        messages.success(self.request, "Login successful.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Invalid login credentials.")
        return super().form_invalid(form)

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')

def all_routes_with_vehicles(request):
    routes = Route.objects.select_related('vehicle').all()
    return render(request, 'route_list.html', {'routes': routes})

def route_detail(request, route_id):
    route = get_object_or_404(Route, id=route_id)
    total_seats = Seat.objects.filter(vehicle=route.vehicle).count()
    booked_seats = Booking.objects.filter(route=route).count()
    available_seats = total_seats - booked_seats
    context = {
        'route': route,
        'available_seats': available_seats,
    }
    return render(request, 'route_detail.html', context)

@login_required
def submit_feedback(request, route_id):
    if request.method == 'POST':
        route = get_object_or_404(Route, id=route_id)

        # Only passengers can submit
        if not request.user.groups.filter(name='Passenger').exists():
            return JsonResponse({'success': False, 'error': 'Permission denied'})

        # Map frontend fields to backend model
        feedback_type = request.POST.get('type')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        # Convert "type" field into appropriate model saving:
        if feedback_type == 'issue':
            # Create an Issue entry instead
            Issue.objects.create(
                user=request.user,
                route=route,
                description=f"[{subject}] {message}"
            )
        else:
            # Create a Feedback entry
            Feedback.objects.create(
                user=request.user,
                route=route,
                rating=5,  # Default rating if not provided in form
                comment=f"({feedback_type.upper()}) {subject} - {message}"
            )

        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def submit_issue(request):
    if request.method == 'POST':
        description = request.POST.get('description')
        route_id = request.POST.get('route_id')
        booking_id = request.POST.get('booking_id')

        route = Route.objects.filter(id=route_id).first()
        booking = Booking.objects.filter(id=booking_id).first()

        Issue.objects.create(
            user=request.user,
            route=route,
            booking=booking,
            description=description
        )
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid method'})

@login_required
def submit_feedback_global(request):
    if request.method == "POST":
        feedback_type = request.POST.get("type")
        subject = request.POST.get("subject")
        message = request.POST.get("message")
        route_id = request.POST.get("route_id")
        booking_id = request.POST.get("booking_id")

        route = None
        booking = None

        # Fetch related objects safely
        if route_id:
            try:
                route = Route.objects.get(id=int(route_id))
            except (Route.DoesNotExist, ValueError):
                route = None

        if booking_id:
            try:
                booking = Booking.objects.get(id=int(booking_id))
            except (Booking.DoesNotExist, ValueError):
                booking = None

        # ✅ Handle different types
        if feedback_type == "feedback" or feedback_type == "suggestion":
            Feedback.objects.create(
                user=request.user,
                route=route,
                rating=5,  # default if you’re not collecting rating in the modal
                comment=f"{subject}\n\n{message}"
            )
        elif feedback_type == "issue":
            Issue.objects.create(
                user=request.user,
                route=route,
                booking=booking,
                description=f"{subject}\n\n{message}"
            )
        else:
            return JsonResponse({"success": False, "error": "Invalid feedback type."}, status=400)

        return JsonResponse({"success": True})

    return JsonResponse({"success": False, "error": "Invalid request method."}, status=405)





def ai_assistant(request):
    if request.method != 'POST':
        return JsonResponse({'response': 'Please send your question via POST request.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
        question = data.get('question', '').strip()
    except Exception:
        question = request.POST.get('question', '').strip()

    if not question:
        return JsonResponse({'response': "Please ask a question about routes, vehicles, or fares."})

    try:
        answer = handle_transport_query(question)
        return JsonResponse({'response': answer})
    except Exception as e:
        return JsonResponse({
            'response': f"⚠️ Sorry, something went wrong while processing your request ({str(e)})."
        })

@login_required
def manager_dashboard(request):
    if not request.user.groups.filter(name='Manager').exists():
        messages.error(request, "Access denied.")
        return redirect('home')
    vehicles = Vehicle.objects.filter(manager=request.user)
    routes = Route.objects.filter(vehicle__manager=request.user)
    analytics = {
        'busiest_route': routes.annotate(bookings=Count('booking')).order_by('-bookings').first(),
        'delays': routes.filter(arrival_time__lt=timezone.now()).count(),
    }
    return render(request, 'manager_dashboard.html', {'vehicles': vehicles, 'routes': routes, 'analytics': analytics})

@login_required
def add_update_vehicle(request, pk=None):
    if not request.user.groups.filter(name='Manager').exists():
        messages.error(request, "Access denied.")
        return redirect('home')
    if pk:
        vehicle = get_object_or_404(Vehicle, pk=pk, manager=request.user)
    else:
        vehicle = None
    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.manager = request.user
            vehicle.save()
            messages.success(request, "Vehicle updated successfully.")
            return redirect('manager_dashboard')
    else:
        form = VehicleForm(instance=vehicle)
    return render(request, 'add_update_vehicle.html', {'form': form})

@login_required
def monitor_map(request):
    if not request.user.groups.filter(name='Manager').exists():
        messages.error(request, "Access denied.")
        return redirect('home')
    return render(request, 'monitor_map.html')

@login_required
def assign_route(request):
    if not request.user.groups.filter(name='Manager').exists():
        messages.error(request, "Access denied.")
        return redirect('home')
    if request.method == 'POST':
        form = RouteForm(request.POST)
        if form.is_valid():
            route = form.save(commit=False)
            route.manager = request.user
            route.save()
            messages.success(request, "Route assigned successfully.")
            return redirect('manager_dashboard')
    else:
        form = RouteForm()
    return render(request, 'assign_route.html', {'form': form})

def vehicle_locations_json(request):
    locations = VehicleLocation.objects.all()
    data = [
        {
            "id": loc.vehicle.id,
            "lat": loc.latitude,
            "lng": loc.longitude,
            "vehicle_name": loc.vehicle.name,
            "route": f"{loc.vehicle.route.start_location} to {loc.vehicle.route.end_location}" if hasattr(loc.vehicle, 'route') and loc.vehicle.route else "N/A"
        } for loc in locations
    ]
    return JsonResponse({"locations": data})


def available_vehicles(request):
    pickup = request.GET.get('pickup', 'Lahore')
    dropoff = request.GET.get('dropoff', 'Islamabad')

    routes = Route.objects.filter(
        start_location__icontains=pickup,
        end_location__icontains=dropoff
    ).select_related('vehicle').prefetch_related('vehicle__seat_set')

    # Pre-calculate available seats
    for route in routes:
        route.available_seats = route.vehicle.seat_set.filter(is_available=True).count()

    context = {
        'routes': routes,
        'pickup': pickup,
        'dropoff': dropoff,
    }
    return render(request, 'available_vehicles.html', context)


def transport_data_api(request):
    routes = Route.objects.select_related('vehicle').filter(
        departure_time__gt=timezone.now()
    ).order_by('departure_time')
    
    data = {
        'vehicles': [],
        'routes': [],
    }

    for vehicle in Vehicle.objects.all():
        available_seats = Seat.objects.filter(
            vehicle=vehicle, is_available=True
        ).count()
        data['vehicles'].append({
            'id': vehicle.id,
            'name': vehicle.name,
            'type': vehicle.vehicle_type,
            'available_seats': available_seats,
        })

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

    return JsonResponse(data)

# views.py
def chatbot_view(request):
    return render(request, 'chatbot.html')

@login_required
def get_user_routes(request):
    routes = Route.objects.filter(booking__user=request.user).distinct()
    data = [
        {"id": r.id, "name": f"{r.start_location} → {r.end_location}"}
        for r in routes
    ]
    return JsonResponse({"routes": data})

@login_required
def get_user_bookings(request):
    bookings = Booking.objects.filter(user=request.user).select_related('route', 'seat')
    data = [
        {
            "id": b.id,
            "name": f"{b} ({b.seat.seat_type} - Rs.{b.seat.fare})"
        }
        for b in bookings
    ]
    return JsonResponse({"bookings": data})
