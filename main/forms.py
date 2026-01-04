from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import CustomUser, Booking, Seat, Route, Feedback, Issue, Vehicle,VehicleLocation

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Email or Username",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email or username'
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
    )


class SeatForm(forms.ModelForm):
    class Meta:
        model = Seat
        fields = ["vehicle", "seat_number", "seat_type", "is_available"]
class CustomRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter email'
    }))
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Choose a username'
    }))
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter password'
    }))
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Confirm password'
    }))

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']

class BookingForm(forms.ModelForm):
    seats = forms.ModelMultipleChoiceField(
        queryset=Seat.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    class Meta:
        model = Booking
        fields = ['seats']  # 🔥 REMOVE fare COMPLETELY

    def __init__(self, *args, **kwargs):
        route = kwargs.pop('route', None)
        super().__init__(*args, **kwargs)

        if route:
            self.route = route
            self.fields['seats'].queryset = Seat.objects.filter(
                vehicle=route.vehicle,
                is_available=True
            )

    def clean_seats(self):
        seats = self.cleaned_data.get("seats")

        if not seats:
            raise forms.ValidationError("Please select at least one seat.")

        return seats

        

class RouteForm(forms.ModelForm):
    class Meta:
        model = Route
        fields = ['vehicle', 'start_location', 'end_location', 'departure_time', 'arrival_time', 'fare', 'image']
        widgets = {
            'departure_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'arrival_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'fare': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class FeedbackForm(forms.ModelForm):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]

    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect,
        label="Rating",
        required=True
    )

    class Meta:
        model = Feedback
        fields = ['route', 'comment', 'rating']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['route'].queryset = Route.objects.all().order_by('start_location')
        self.fields['route'].empty_label = "-- Select a Route --"
        self.fields['route'].label = "Route"
        self.fields['comment'].label = "Comment"

    def clean_rating(self):
        rating = self.cleaned_data['rating']
        return int(rating)

class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ['booking', 'route', 'description']
        widgets = {
            'booking': forms.Select(attrs={'class': 'form-control'}),
            'route': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe the issue'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['booking'].queryset = Booking.objects.filter(user=user)
            self.fields['route'].queryset = Route.objects.filter(booking__user=user).distinct()

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['name', 'number_plate', 'driver', 'manager', 'status', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'number_plate': forms.TextInput(attrs={'class': 'form-control'}),
            'driver': forms.Select(attrs={'class': 'form-control'}),
            'manager': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class VehicleLocationForm(forms.ModelForm):
    class Meta:
        model = VehicleLocation
        fields = ['latitude', 'longitude']
        labels = {
            'latitude': 'Vehicle Position (North/South)',
            'longitude': 'Vehicle Position (East/West)',
        }

class RouteForm(forms.ModelForm):
    class Meta:
        model = Route
        fields = ['vehicle', 'start_location', 'end_location', 'departure_time', 'arrival_time', 'fare', 'vip_seats', 'std_seats']
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-control'}),
            'start_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Hostel'}),
            'end_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Main Campus'}),
            'departure_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'arrival_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'fare': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 500'}),
            'vip_seats': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 10'}),
            'std_seats': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 20'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        departure_time = cleaned_data.get('departure_time')
        arrival_time = cleaned_data.get('arrival_time')
        vip_seats = cleaned_data.get('vip_seats')
        std_seats = cleaned_data.get('std_seats')

        if departure_time and arrival_time and departure_time >= arrival_time:
            raise forms.ValidationError("Departure time must be before arrival time.")
        if vip_seats is not None and vip_seats < 0:
            raise forms.ValidationError("VIP seats cannot be negative.")
        if std_seats is not None and std_seats < 0:
            raise forms.ValidationError("Standard seats cannot be negative.")
        return cleaned_data