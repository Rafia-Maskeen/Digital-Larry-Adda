import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from django.utils import timezone
from .models import Vehicle, Route, Seat, Booking


def format_datetime(dt):
    return dt.strftime('%a, %d %b %Y, %I:%M %p')


def seats_left(route):
    total = Seat.objects.filter(vehicle=route.vehicle).count()
    booked = Booking.objects.filter(route=route).count()
    return max(0, total - booked)


def is_greeting(text: str) -> bool:
    """
    Return True only if the message looks like a greeting,
    not a real question.
    """
    text = text.strip().lower()
    greetings = {"hi", "hello", "hey", "hy", "salam"}
    return text in greetings or text.startswith(("good morning", "good evening"))


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def detect_day_range(question: str):
    """Detect if user mentioned a day (today, tomorrow, tonight, morning, evening)."""
    now = timezone.now()
    tomorrow = now + timedelta(days=1)
    q = question.lower().strip()

    # Default = next 7 days
    start = now
    end = now + timedelta(days=7)

    if "today" in q:
        start = now.replace(hour=0, minute=0, second=0)
        end = now.replace(hour=23, minute=59, second=59)
    elif any(word in q for word in ["tomorrow", "tomottow", "tommorow"]):
        start = tomorrow.replace(hour=0, minute=0, second=0)
        end = tomorrow.replace(hour=23, minute=59, second=59)
    elif any(word in q for word in ["tonight", "evening"]):
        start = now.replace(hour=18, minute=0, second=0)
        end = now.replace(hour=23, minute=59, second=59)
    elif "morning" in q:
        start = now.replace(hour=6, minute=0, second=0)
        end = now.replace(hour=12, minute=0, second=0)

    return start, end


def handle_transport_query(question: str) -> str:
    question = question.strip().lower()
    if not question:
        return (
            "Please type a question — for example:\n"
            "• Next bus\n• Available routes\n• Fare from Lahore to Islamabad"
        )

    now = timezone.now()
    routes = Route.objects.select_related('vehicle').filter(departure_time__gte=now).order_by('departure_time')
    vehicles = Vehicle.objects.all()

    # 1️⃣ Greetings
    if is_greeting(question):
        return (
            "Hello! 👋 I'm your transport assistant.\n\n"
            "You can ask things like:\n"
            "• Next bus\n"
            "• Available vehicles\n"
            "• Bus to Islamabad\n"
            "• Lahore to Karachi route\n"
            "• Fare from Lahore to Islamabad\n"
            "• Routes for tomorrow or tonight\n"
            "• Seats from Kotli to Mirpur"
        )

    # 2️⃣ Date-based route questions
    if any(word in question for word in ["today", "tomorrow", "tomottow", "tommorow", "tonight", "morning", "evening"]):
        start, end = detect_day_range(question)
        matching_routes = Route.objects.filter(departure_time__range=(start, end)).order_by('departure_time')

        if matching_routes.exists():
            msg_lines = []
            for r in matching_routes[:5]:
                msg_lines.append(
                    f"🚌 {r.start_location} → {r.end_location} | {r.vehicle.name} | "
                    f"{format_datetime(r.departure_time)} | Rs. {r.fare} | Seats: {seats_left(r)}"
                )
            readable_day = "tomorrow" if "tomorrow" in question or "tomottow" in question else "today"
            return f"✅ Here are the routes scheduled for {readable_day.capitalize()}:\n" + "\n".join(msg_lines)
        else:
            readable_day = "tomorrow" if "tomorrow" in question or "tomottow" in question else "today"
            return f"⚠️ No routes are currently scheduled for {readable_day.capitalize()}. Please check again later."

    # 3️⃣ Fare-related intent
    if any(word in question for word in ["fare", "price", "cost"]):
        match = re.findall(r"[A-Z]?[a-z]+", question.title())
        if len(match) >= 1:
            city = match[-1]
            matched_routes = routes.filter(start_location__icontains=city) | routes.filter(end_location__icontains=city)
            if matched_routes.exists():
                fares = [r.fare for r in matched_routes[:3]]
                avg_fare = sum(fares) / len(fares)
                return (
                    f"The average base fare for routes involving **{city}** is around Rs. {avg_fare:.0f}.\n"
                    f"Try asking more specifically, like *fare from {city} to Mirpur*."
                )
            return f"I couldn’t find any active routes related to **{city}**."
        return "Please specify at least one location, for example *fare for Lahore to Islamabad*."

    # 4️⃣ Next bus or route
    if any(kw in question for kw in ["next bus", "next route", "next ride"]):
        nxt = routes.first()
        if nxt:
            return (
                f"🚌 The next route is **{nxt.start_location} → {nxt.end_location}**.\n"
                f"Vehicle: {nxt.vehicle.name}\n"
                f"Departure: {format_datetime(nxt.departure_time)}\n"
                f"Base Fare: Rs. {nxt.fare}\n"
                f"Seats Available: {seats_left(nxt)}"
            )
        return "No upcoming routes are scheduled right now."

    # 5️⃣ Available vehicles
    if any(kw in question for kw in ["available vehicles", "vehicles available", "show vehicles", "list vehicles"]):
        vehicles_list = []
        for v in vehicles:
            count = Seat.objects.filter(vehicle=v, is_available=True).count()
            vehicles_list.append(f"{v.name} — {count} seats available")
        if vehicles_list:
            return "🚍 Available vehicles:\n" + "\n".join(f"• {v}" for v in vehicles_list)
        return "No vehicles are currently showing available seats."

    # 6️⃣ Seat or route inquiries
    if any(word in question for word in ["seat", "seats", "route", "bus"]):
        words = re.findall(r"[A-Z]?[a-z]+", question.title())
        if len(words) >= 2:
            start_city, end_city = words[-2], words[-1]
            matched = routes.filter(start_location__icontains=start_city, end_location__icontains=end_city)
            if not matched.exists():
                matched = routes.filter(start_location__icontains=end_city, end_location__icontains=start_city)
            if matched.exists():
                lines = []
                for r in matched[:5]:
                    lines.append(
                        f"🚌 {r.start_location} → {r.end_location} | {r.vehicle.name} | "
                        f"{format_datetime(r.departure_time)} | Rs. {r.fare} | Seats: {seats_left(r)}"
                    )
                return "Here are the matching routes:\n" + "\n".join(lines)
            else:
                return f"⚠️ No routes found for {start_city} to {end_city}."

    # 7️⃣ Default fallback
    return (
        "Hello! 👋 I can help you with transport info.\n\n"
        "Try asking things like:\n"
        "• Next bus\n"
        "• Available vehicles\n"
        "• Bus to Islamabad\n"
        "• Lahore to Karachi route\n"
        "• Fare from Lahore to Islamabad\n"
        "• Routes for tomorrow\n"
        "• Seats from Kotli to Mirpur"
    )
def handle_transport_query(question: str) -> str:
    question = question.strip().lower()
    if not question:
        return (
            "Please type a question — for example:\n"
            "• Next bus\n• Available routes\n• Fare from Lahore to Islamabad"
        )

    now = timezone.now()
    routes = Route.objects.select_related('vehicle').filter(departure_time__gte=now).order_by('departure_time')
    vehicles = Vehicle.objects.all()

    # 1️⃣ Greetings
    if is_greeting(question):
        return (
            "Hello! 👋 I'm your transport assistant.\n\n"
            "You can ask things like:\n"
            "• Next bus\n"
            "• Available vehicles\n"
            "• Bus to Islamabad\n"
            "• Lahore to Karachi route\n"
            "• Fare from Lahore to Islamabad\n"
            "• Routes for tomorrow or tonight\n"
            "• Seats from Kotli to Mirpur"
        )

    # 2️⃣ Date-based route questions
    if any(word in question for word in ["today", "tomorrow", "tomottow", "tommorow", "tonight", "morning", "evening"]):
        start, end = detect_day_range(question)
        matching_routes = Route.objects.filter(departure_time__range=(start, end)).order_by('departure_time')

        if matching_routes.exists():
            msg_lines = []
            for r in matching_routes[:5]:
                msg_lines.append(
                    f"🚌 {r.start_location} → {r.end_location} | {r.vehicle.name} | "
                    f"{format_datetime(r.departure_time)} | Rs. {r.fare} | Seats: {seats_left(r)}"
                )
            readable_day = "tomorrow" if "tomorrow" in question or "tomottow" in question else "today"
            return f"✅ Here are the routes scheduled for {readable_day.capitalize()}:\n" + "\n".join(msg_lines)
        else:
            readable_day = "tomorrow" if "tomorrow" in question or "tomottow" in question else "today"
            return f"⚠️ No routes are currently scheduled for {readable_day.capitalize()}. Please check again later."

    # 3️⃣ Fare-related intent
    if any(word in question for word in ["fare", "price", "cost"]):
        match = re.findall(r"[A-Z]?[a-z]+", question.title())
        if len(match) >= 1:
            city = match[-1]
            matched_routes = routes.filter(start_location__icontains=city) | routes.filter(end_location__icontains=city)
            if matched_routes.exists():
                fares = [r.fare for r in matched_routes[:3]]
                avg_fare = sum(fares) / len(fares)
                return (
                    f"The average base fare for routes involving **{city}** is around Rs. {avg_fare:.0f}.\n"
                    f"Try asking more specifically, like *fare from {city} to Mirpur*."
                )
            return f"I couldn’t find any active routes related to **{city}**."
        return "Please specify at least one location, for example *fare for Lahore to Islamabad*."

    # 4️⃣ Next bus or route
    if any(kw in question for kw in ["next bus", "next route", "next ride"]):
        nxt = routes.first()
        if nxt:
            return (
                f"🚌 The next route is **{nxt.start_location} → {nxt.end_location}**.\n"
                f"Vehicle: {nxt.vehicle.name}\n"
                f"Departure: {format_datetime(nxt.departure_time)}\n"
                f"Base Fare: Rs. {nxt.fare}\n"
                f"Seats Available: {seats_left(nxt)}"
            )
        return "No upcoming routes are scheduled right now."

    # 5️⃣ Available vehicles
    if any(kw in question for kw in ["available vehicles", "vehicles available", "show vehicles", "list vehicles"]):
        vehicles_list = []
        for v in vehicles:
            count = Seat.objects.filter(vehicle=v, is_available=True).count()
            vehicles_list.append(f"{v.name} — {count} seats available")
        if vehicles_list:
            return "🚍 Available vehicles:\n" + "\n".join(f"• {v}" for v in vehicles_list)
        return "No vehicles are currently showing available seats."

    # 6️⃣ Vehicle-specific questions
    for v in vehicles:
        if v.name.lower() in question:
            count = Seat.objects.filter(vehicle=v, is_available=True).count()
            total = Seat.objects.filter(vehicle=v).count()
            route_list = Route.objects.filter(vehicle=v)
            if route_list.exists():
                r = route_list.first()
                route_info = f"Currently assigned to route: {r.start_location} → {r.end_location}"
            else:
                route_info = "No active route assigned currently."

            return (
                f"🚐 Vehicle: **{v.name}**\n"
                f"Status: {v.status}\n"
                f"Total Seats: {total}\n"
                f"Available Seats: {count}\n"
                f"{route_info}"
            )

    # 7️⃣ Seat or route inquiries (default)
    if any(word in question for word in ["seat", "seats", "route", "bus"]):
        words = re.findall(r"[A-Z]?[a-z]+", question.title())
        if len(words) >= 2:
            start_city, end_city = words[-2], words[-1]
            matched = routes.filter(start_location__icontains=start_city, end_location__icontains=end_city)
            if not matched.exists():
                matched = routes.filter(start_location__icontains=end_city, end_location__icontains=start_city)
            if matched.exists():
                lines = []
                for r in matched[:5]:
                    lines.append(
                        f"🚌 {r.start_location} → {r.end_location} | {r.vehicle.name} | "
                        f"{format_datetime(r.departure_time)} | Rs. {r.fare} | Seats: {seats_left(r)}"
                    )
                return "Here are the matching routes:\n" + "\n".join(lines)
            else:
                return f"⚠️ No routes found for {start_city} to {end_city}."

    # 8️⃣ Default fallback
    return (
        "Hello! 👋 I can help you with transport info.\n\n"
        "Try asking things like:\n"
        "• Next bus\n"
        "• Available vehicles\n"
        "• Bus to Islamabad\n"
        "• Lahore to Karachi route\n"
        "• Fare from Lahore to Islamabad\n"
        "• Routes for tomorrow\n"
        "• Seats from Kotli to Mirpur"
    )
