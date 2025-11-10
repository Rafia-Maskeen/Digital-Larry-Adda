import difflib
from datetime import timedelta
from django.utils import timezone
from .models import Vehicle, Route, Seat, Booking, VehicleLocation


def handle_transport_query(question: str):
    q = question.lower().strip()
    q = q.replace("tomorow", "tomorrow")
    greet = get_greeting_response(q)
    if greet:
        return greet
    # ✅ If the user mentions "vehicle(s)", prefer vehicle intent even if "available" is present
    if any(k in q for k in ["vehicle", "vehicles", "bus list", "buses"]):
        return get_vehicle_info(q)

    if any(k in q for k in ["fare", "price", "cost", "ticket"]):
        return get_fare_info(q)

    if any(k in q for k in ["time", "timing", "schedule", "when", "next bus"]):
        return get_route_timing(q)

    # Seats intent AFTER vehicle intent, so "available vehicles" doesn’t get misrouted
    if any(k in q for k in ["seat", "available", "availability", "how many"]):
        return get_seat_info(q)

    if any(k in q for k in ["route", "routes", "bus", "travel", "go to"]):
        return get_routes_info(q)

    if any(k in q for k in ["location", "where"]):
        return get_vehicle_location_info(q)

    if any(k in q for k in ["booking", "bookings"]):
        return get_booking_info(q)

    return "🤖 Could you clarify? Try: 'available vehicles', 'fare Kotli to Mirpur', or 'routes for tomorrow'."

# ------------------------ HELPERS ------------------------

def find_city_pair(q, routes):
    """Return (start, end) if cities appear in query, even partially."""
    cities = {r.start_location.lower() for r in routes} | {r.end_location.lower() for r in routes}
    words = q.split()
    found = []
    for w in words:
        match = difflib.get_close_matches(w, cities, n=1, cutoff=0.7)
        if match:
            found.append(match[0])
    if len(found) >= 2:
        return found[0], found[1]
    elif len(found) == 1:
        return found[0], None
    return None, None


def get_routes_info(q):
    routes = Route.objects.select_related('vehicle').order_by('departure_time')
    if not routes.exists():
        return "No routes have been added yet."

    start_city, end_city = find_city_pair(q, routes)

    # Tomorrow filter
    if "tomorrow" in q:
        tomorrow = timezone.now().date() + timedelta(days=1)
        tomorrow_routes = routes.filter(departure_time__date=tomorrow)
        if tomorrow_routes.exists():
            msg = ["🗓️ Routes scheduled for tomorrow:"]
            for r in tomorrow_routes:
                msg.append(f"- {r.start_location} → {r.end_location} ({r.vehicle.name}) at {r.departure_time.strftime('%H:%M')} | Rs.{r.fare}")
            return "\n".join(msg)
        # fallback to next available
        upcoming = routes.filter(departure_time__gt=timezone.now())[:3]
        if upcoming.exists():
            msg = ["🕒 No routes exactly tomorrow, but here are the next ones:"]
            for r in upcoming:
                msg.append(f"- {r.start_location} → {r.end_location} ({r.vehicle.name}) at {r.departure_time.strftime('%d %b %H:%M')}")
            return "\n".join(msg)
        return "No upcoming routes found."

    # If user mentioned cities
    if start_city:
        qs = routes.filter(start_location__icontains=start_city)
        if end_city:
            qs = qs.filter(end_location__icontains=end_city)
            if not qs.exists():
                qs = routes.filter(start_location__icontains=end_city, end_location__icontains=start_city)
        if qs.exists():
            msg = [f"🚌 Routes involving {start_city.title()}" + (f" and {end_city.title()}:" if end_city else ":")]
            for r in qs:
                msg.append(f"- {r.start_location} → {r.end_location} | {r.vehicle.name} at {r.departure_time.strftime('%Y-%m-%d %H:%M')} | Rs.{r.fare}")
            return "\n".join(msg)
        return f"No routes found near {start_city.title()}."

    # General fallback
    msg = ["🚍 Upcoming Routes:"]
    for r in routes[:5]:
        msg.append(f"- {r.start_location} → {r.end_location} ({r.vehicle.name}) at {r.departure_time.strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(msg)


def get_route_timing(q):
    """Return timing for a route between two cities."""
    routes = Route.objects.select_related('vehicle')
    start, end = find_city_pair(q, routes)
    if not start or not end:
        # fallback to next route
        upcoming = routes.filter(departure_time__gt=timezone.now()).order_by('departure_time')[:3]
        if not upcoming.exists():
            return "No routes scheduled yet."
        msg = ["🕒 Next scheduled routes:"]
        for r in upcoming:
            msg.append(f"- {r.start_location} → {r.end_location} ({r.vehicle.name}) at {r.departure_time.strftime('%Y-%m-%d %H:%M')}")
        return "\n".join(msg)

    qs = routes.filter(start_location__icontains=start, end_location__icontains=end)
    if not qs.exists():
        qs = routes.filter(start_location__icontains=end, end_location__icontains=start)
    if not qs.exists():
        return f"No routes found between {start.title()} and {end.title()}."
    msg = [f"🕒 Timings for {start.title()} → {end.title()}:"]
    for r in qs:
        msg.append(f"- {r.vehicle.name} departs {r.departure_time.strftime('%Y-%m-%d %H:%M')} | Rs.{r.fare}")
    return "\n".join(msg)


def get_fare_info(q):
    routes = Route.objects.select_related('vehicle')
    start, end = find_city_pair(q, routes)
    if not start or not end:
        return "Please mention both cities (e.g. 'fare from Kotli to Mirpur')."

    qs = routes.filter(start_location__icontains=start, end_location__icontains=end)
    if not qs.exists():
        qs = routes.filter(start_location__icontains=end, end_location__icontains=start)
    if not qs.exists():
        return f"No fare data found between {start.title()} and {end.title()}."

    msg = [f"💰 Fare between {start.title()} and {end.title()}:"]
    for r in qs:
        msg.append(f"- {r.vehicle.name}: Rs.{r.fare}")
    return "\n".join(msg)


def get_seat_info(q):
    routes = Route.objects.select_related('vehicle')
    start, end = find_city_pair(q, routes)
    if start and end:
        route = routes.filter(start_location__icontains=start, end_location__icontains=end).first()
        if not route:
            route = routes.filter(start_location__icontains=end, end_location__icontains=start).first()
        if not route:
            return f"No route found between {start.title()} and {end.title()}."
        total = Seat.objects.filter(vehicle=route.vehicle).count()
        available = Seat.objects.filter(vehicle=route.vehicle, is_available=True).count()
        return f"💺 {available} out of {total} seats available on {route.vehicle.name} for the {start.title()} → {end.title()} route."

    available = Seat.objects.filter(is_available=True).select_related('vehicle')
    if not available.exists():
        return "No seats available right now."
    msg = ["💺 Available seats:"]
    for s in available[:10]:
        msg.append(f"- {s.vehicle.name}: {s.seat_number} ({s.get_seat_type_display()}) — Rs.{s.fare}")
    return "\n".join(msg)


from .models import Vehicle, Seat  # ensure Seat is imported

def get_vehicle_info(q):
    vehicles = Vehicle.objects.all()

    # filter by status if asked
    if "active" in q:
        vehicles = vehicles.filter(status="Active")
    elif "broken" in q:
        vehicles = vehicles.filter(status="Broken")

    # ✅ special case: "available vehicles" -> only vehicles with >0 available seats
    if "available" in q:
        result = []
        for v in vehicles:
            avail = Seat.objects.filter(vehicle=v, is_available=True).count()
            if avail > 0:
                result.append((v, avail))

        if not result:
            return "No vehicles with available seats right now."

        lines = ["🚗 Vehicles with available seats:"]
        for v, avail in result[:10]:
            lines.append(f"- {v.name} ({v.number_plate}) — {avail} seats available · Status: {v.status}")
        return "\n".join(lines)

    # default listing
    if not vehicles.exists():
        return "No vehicles found."

    lines = ["🚗 Vehicles:"]
    for v in vehicles[:10]:
        lines.append(f"- {v.name} ({v.number_plate}) — Status: {v.status}, Driver: {v.driver or 'Unassigned'}")
    return "\n".join(lines)



def get_booking_info(q):
    bookings = Booking.objects.select_related('user', 'route', 'seat').order_by('-id')
    if not bookings.exists():
        return "No bookings yet."
    msg = ["📘 Recent bookings:"]
    for b in bookings[:5]:
        msg.append(f"- {b.user.username}: {b.route.start_location} → {b.route.end_location} | {b.seat.seat_number} ({b.seat.get_seat_type_display()}) - {b.status}")
    return "\n".join(msg)


def get_vehicle_location_info(q):
    locs = VehicleLocation.objects.select_related('vehicle')
    if not locs.exists():
        return "No location data available."
    msg = ["📍 Latest vehicle locations:"]
    for l in locs[:5]:
        msg.append(f"- {l.vehicle.name}: ({l.latitude:.3f}, {l.longitude:.3f}) updated {l.timestamp.strftime('%H:%M')}")
    return "\n".join(msg)

def get_greeting_response(q):
    """Respond nicely to greetings or casual chat."""
    greetings = ["hi", "hello", "hey", "salam", "good morning", "good evening", "good afternoon"]
    if any(g in q for g in greetings):
        return (
            "👋 Hello there! I'm your AI Transport Assistant.\n\n"
            "You can ask me things like:\n"
            "• Next bus\n"
            "• Available vehicles\n"
            "• Fare from Kotli to Mirpur\n"
            "• Seats available for tomorrow\n"
            "• Vehicle locations\n"
        )

    if "how are you" in q:
        return "🤖 I'm just a bunch of code, but I'm running smoothly! How can I assist you today?"

    if "who are you" in q or "what can you do" in q:
        return (
            "🧠 I'm your transport assistant! I can help you with:\n"
            "- Bus routes and schedules\n"
            "- Seat availability\n"
            "- Fare details\n"
            "- Vehicle information\n"
            "- Booking summaries"
        )

    return None
