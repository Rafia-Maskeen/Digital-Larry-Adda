import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout,authenticate
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
from .models import AdminMessage
from django.core.mail import send_mail
from django.core.serializers import serialize
from django.db.models import F
from .assistant_engine import handle_transport_query
from django.conf import settings
from .models import AIInteraction, Vehicle, Route, Seat, Booking, Feedback, Issue, VehicleLocation
from .forms import CustomLoginForm, CustomRegisterForm, BookingForm,  VehicleForm, RouteForm, SeatForm, VehicleLocationForm, FeedbackForm, IssueForm

def home(request):
    return render(request, 'home/index.html')

def about(request):
    return render(request, 'home/about.html')

def contact(request):
    return render(request, 'home/contact.html')

def custom_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            # Redirect by role
            if user.groups.filter(name="Manager").exists():
                return redirect("manager_dashboard")
            elif user.groups.filter(name="Driver").exists():
                return redirect("driver_dashboard")
            else:
                return redirect("home")
    return render(request, "login.html")

def find_ride(request):
    return render(request, 'vehicle/find_ride.html')

def vehicles(request):
    vehicles = Vehicle.objects.all()
    return render(request, 'vehicle/vehicles_list.html', {'vehicles': vehicles})

def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    routes = Route.objects.filter(vehicle=vehicle).order_by('departure_time')
    empty_seats = Seat.objects.filter(vehicle=vehicle, is_available=True).count()
    expected_time = timedelta(hours=1)
    return render(request, 'vehicle/vehicle_detail.html', {
        'vehicle': vehicle,
        'routes': routes,
        'empty_seats': empty_seats,
        'expected_time': expected_time
    })

def available_vehicles(request):
    pickup = request.GET.get('pickup')
    dropoff = request.GET.get('dropoff')
    routes = Route.objects.filter(start_location__icontains=pickup, end_location__icontains=dropoff)
    return render(request, 'vehicle/available_vehicles.html', {'routes': routes, 'pickup': pickup, 'dropoff': dropoff})

def book_route(request, route_id):
    route = get_object_or_404(Route, id=route_id)

    if request.method == "POST":
        form = BookingForm(request.POST, route=route)

        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.route = route
            booking.save()

            booking.seats.set(form.cleaned_data["seats"])

            # Mark seats as booked
            form.cleaned_data["seats"].update(is_available=False)

            messages.success(request, "Booking successful!")
            return redirect("booking_success")

        else:
            messages.error(request, "Something went wrong! Check your selection.")

    else:
        form = BookingForm(route=route)

    return render(request, "routes/book_route.html", {
        'route': route,
        'form': form
    })


@login_required
def booking_success(request):
    return render(request, 'routes/booking_success.html')

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
    return render(request, 'auth/register.html', {'form': form})

class CustomLoginView(LoginView):
    form_class = CustomLoginForm
    template_name = 'auth/login.html'
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
    return render(request, 'routes/route_list.html', {'routes': routes})

def route_detail(request, route_id):
    route = get_object_or_404(Route, id=route_id)
    total_seats = Seat.objects.filter(vehicle=route.vehicle).count()
    booked_seats = Booking.objects.filter(route=route).count()
    available_seats = total_seats - booked_seats
    context = {
        'route': route,
        'available_seats': available_seats,
    }
    return render(request, 'routes/route_detail.html', context)

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
def feedback_list(request):
    feedbacks = Feedback.objects.filter(user=request.user)
    return render(request, 'feedback/feedback_list.html', {'feedbacks': feedbacks})

@login_required
def feedback_add(request):
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            fb = form.save(commit=False)
            fb.user = request.user
            fb.save()
            return redirect('feedback_list')
    else:
        form = FeedbackForm()
    return render(request, 'feedback/feedback_form.html', {'form': form, 'title': 'Add Feedback'})

@login_required
def feedback_edit(request, pk):
    feedback = get_object_or_404(Feedback, pk=pk, user=request.user)
    if request.method == 'POST':
        form = FeedbackForm(request.POST, instance=feedback)
        if form.is_valid():
            form.save()
            return redirect('feedback_list')
    else:
        form = FeedbackForm(instance=feedback)
    return render(request, 'feedback/feedback_form.html', {'form': form, 'title': 'Edit Feedback'})

@login_required
def feedback_delete(request, pk):
    feedback = get_object_or_404(Feedback, pk=pk, user=request.user)
    if request.method == 'POST':
        feedback.delete()
        return redirect('feedback_list')
    return render(request, 'feedback/feedback_confirm_delete.html', {'feedback': feedback})

@login_required
def issue_list(request):
    issues = Issue.objects.filter(user=request.user)
    return render(request, 'issue/issue_list.html', {'issues': issues})

@login_required
def issue_add(request):
    if request.method == 'POST':
        form = IssueForm(request.POST)
        if form.is_valid():
            issue = form.save(commit=False)
            issue.user = request.user
            issue.save()
            return redirect('issue_list')
    else:
        form = IssueForm()
    return render(request, 'issue/issue_form.html', {'form': form, 'title': 'Report Issue'})

@login_required
def issue_edit(request, pk):
    issue = get_object_or_404(Issue, pk=pk, user=request.user)
    if request.method == 'POST':
        form = IssueForm(request.POST, instance=issue)
        if form.is_valid():
            form.save()
            return redirect('issue_list')
    else:
        form = IssueForm(instance=issue)
    return render(request, 'issue/issue_form.html', {'form': form, 'title': 'Edit Issue'})

@login_required
def issue_delete(request, pk):
    issue = get_object_or_404(Issue, pk=pk, user=request.user)
    if request.method == 'POST':
        issue.delete()
        return redirect('issue_list')
    return render(request, 'issue/issue_confirm_delete.html', {'issue': issue})




@login_required
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
        # 👇 Call your logic function
        answer = handle_transport_query(question)

        # 💾 Log the chat
        AIInteraction.objects.create(
            user=request.user,
            question=question,
            response=answer
        )

        return JsonResponse({'response': answer})
    except Exception as e:
        return JsonResponse({
            'response': f"⚠️ Sorry, something went wrong: {str(e)}"
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
    return render(request, 'manager/manager_dashboard.html', {'vehicles': vehicles, 'routes': routes, 'analytics': analytics})

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
    return render(request, 'vehicle/add_update_vehicle.html', {'form': form})

@login_required
def monitor_map(request):
    if not request.user.groups.filter(name='Manager').exists():
        messages.error(request, "Access denied.")
        return redirect('home')
    return render(request, 'manager/monitor_map.html')

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
    return render(request, 'routes/assign_route.html', {'form': form})

def vehicle_locations_json(request):
    locations = VehicleLocation.objects.select_related('vehicle', 'vehicle__route').values(
        'id',
        'vehicle__name',
        'vehicle__route__start_location',
        'vehicle__route__end_location',
        'lat',
        'lng',
        'status'
    )
    data = {
        "locations": [
            {
                "id": l["id"],
                "vehicle_name": l["vehicle__name"],
                "route": f"{l['vehicle__route__start_location']} → {l['vehicle__route__end_location']}" if l["vehicle__route__start_location"] else "N/A",
                "lat": l["lat"],
                "lng": l["lng"],
                "status": l["status"],
            }
            for l in locations
        ]
    }
    return JsonResponse(data)


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
    return render(request, 'vehicle/available_vehicles.html', context)

@login_required
def driver_vehicle_location_list(request):
    if not request.user.groups.filter(name="Driver").exists():
        return redirect("home")
    locations = VehicleLocation.objects.filter(vehicle__driver=request.user)
    return render(request, "driver/vehicle_location_list.html", {"locations": locations})


@login_required
def driver_vehicle_location_add(request):
    if not request.user.groups.filter(name="Driver").exists():
        return redirect("home")

    if request.method == "POST":
        form = VehicleLocationForm(request.POST)
        if form.is_valid():
            loc = form.save(commit=False)
            loc.vehicle = Vehicle.objects.get(driver=request.user)
            loc.save()
            return redirect("driver_vehicle_location_list")
    else:
        form = VehicleLocationForm()
    return render(request, "driver/vehicle_location_add.html", {"form": form})


@login_required
def driver_vehicle_location_edit(request, loc_id):
    if not request.user.groups.filter(name="Driver").exists():
        return redirect("home")

    location = get_object_or_404(VehicleLocation, id=loc_id, vehicle__driver=request.user)
    if request.method == "POST":
        form = VehicleLocationForm(request.POST, instance=location)
        if form.is_valid():
            form.save()
            return redirect("driver_vehicle_location_list")
    else:
        form = VehicleLocationForm(instance=location)
    return render(request, "driver/vehicle_location_edit.html", {"form": form, "location": location})


@login_required
def driver_vehicle_location_delete(request, loc_id):
    if not request.user.groups.filter(name="Driver").exists():
        return redirect("home")

    location = get_object_or_404(VehicleLocation, id=loc_id, vehicle__driver=request.user)
    location.delete()
    return redirect("driver_vehicle_location_list")

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

@login_required
def driver_dashboard(request):
    """Show all data related to this driver's routes and vehicles."""

    # Make sure this user is a driver
    if not request.user.groups.filter(name="Driver").exists():
        return redirect("home")

    # 1️⃣ Get all vehicles assigned to this driver
    vehicles = Vehicle.objects.filter(driver=request.user)

    # 2️⃣ Get all routes that use these vehicles
    routes = Route.objects.filter(vehicle__in=vehicles)

    # 3️⃣ Get bookings related to those routes
    bookings = Booking.objects.filter(route__in=routes).select_related("route", "user", "seat")

    # 4️⃣ Get feedback and issues related to those routes
    feedback = Feedback.objects.filter(route__in=routes)
    issues = Issue.objects.filter(route__in=routes)

    # 5️⃣ Vehicle locations
    locations = VehicleLocation.objects.filter(vehicle__in=vehicles)

    return render(
        request,
        "driver/driver_dashboard.html",
        {
            "vehicles": vehicles,
            "routes": routes,
            "bookings": bookings,
            "feedback": feedback,
            "issues": issues,
            "locations": locations,
        },
    )

def driver_seat_list(request):
    seats = Seat.objects.filter(vehicle__driver=request.user)
    return render(request, "driver/seat_list.html", {"seats": seats})


@login_required
def driver_seat_add(request):
    """Add a seat for one of the driver's vehicles."""
    if not request.user.groups.filter(name="Driver").exists():
        return redirect("home")

    if request.method == "POST":
        form = SeatForm(request.POST)
        if form.is_valid():
            seat = form.save(commit=False)
            # Prevent adding to another driver’s vehicle
            if seat.vehicle.driver != request.user:
                messages.error(request, "You can only add seats to your own vehicles.")
                return redirect("driver_seat_list")
            seat.save()
            messages.success(request, "Seat added successfully.")
            return redirect("driver_seat_list")
    else:
        form = SeatForm()

    form.fields["vehicle"].queryset = Vehicle.objects.filter(driver=request.user)
    return render(request, "driver/seat_form.html", {"form": form, "title": "Add Seat"})


@login_required
def driver_seat_edit(request, seat_id):
    """Edit a specific seat."""
    if not request.user.groups.filter(name="Driver").exists():
        return redirect("home")

    seat = get_object_or_404(Seat, id=seat_id, vehicle__driver=request.user)

    if request.method == "POST":
        form = SeatForm(request.POST, instance=seat)
        if form.is_valid():
            form.save()
            messages.success(request, "Seat updated successfully.")
            return redirect("driver_seat_list")
    else:
        form = SeatForm(instance=seat)

    form.fields["vehicle"].queryset = Vehicle.objects.filter(driver=request.user)
    return render(request, "driver/seat_form.html", {"form": form, "title": "Edit Seat"})


@login_required
def driver_seat_delete(request, seat_id):
    """Delete a seat belonging to the driver."""
    if not request.user.groups.filter(name="Driver").exists():
        return redirect("home")

    seat = get_object_or_404(Seat, id=seat_id, vehicle__driver=request.user)

    if request.method == "POST":
        seat.delete()
        messages.success(request, "Seat deleted successfully.")
        return redirect("driver_seat_list")

    return render(request, "driver/seat_confirm_delete.html", {"seat": seat})


@login_required
def contact_admin(request):
    if request.method == "POST":
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        # Save message in DB
        AdminMessage.objects.create(
            user=request.user,
            subject=subject,
            message=message
        )

        # Optional: Send email to admin
        try:
            send_mail(
                subject=f"New message from {request.user.username}: {subject}",
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=True,
            )
        except:
            pass

        messages.success(request, "Your message has been sent to admin.")
        return redirect("contact_admin")

    return render(request, "home/contact_admin.html")

def driver_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request, username=username, password=password)

        if not user:
            messages.error(request, "Invalid username or password.")
            return redirect("driver_login")

        # Must be in Driver group
        if not user.groups.filter(name="Driver").exists():
            messages.error(request, "Access denied — This login is for Drivers only.")
            return redirect("driver_login")

        login(request, user)
        messages.success(request, "Welcome Driver!")
        return redirect("driver_dashboard")

    return render(request, "auth/driver_login.html")

def manager_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request, username=username, password=password)

        if not user:
            messages.error(request, "Invalid username or password.")
            return redirect("manager_login")

        # Check Manager group
        if not user.groups.filter(name="Manager").exists():
            messages.error(request, "Access denied — Only Managers can login here.")
            return redirect("manager_login")

        login(request, user)
        messages.success(request, "Welcome Manager!")
        return redirect("manager_dashboard")  # Change to your actual dashboard URL

    return render(request, "auth/manager_login.html")