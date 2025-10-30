from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import CustomUser, Booking, Seat, Route, Feedback, Issue, Vehicle

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
    seat = forms.ModelChoiceField(queryset=None)
    fare = forms.DecimalField(max_digits=10, decimal_places=2, required=True, widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0}))

    def __init__(self, *args, **kwargs):
        route = kwargs.pop('route', None)
        super().__init__(*args, **kwargs)
        if route:
            self.fields['seat'].queryset = Seat.objects.filter(vehicle=route.vehicle, is_available=True)
            # Prepopulate fare based on selected seat
            self.fields['fare'].initial = route.fare  # Optional: Set default fare from route

    class Meta:
        model = Booking
        fields = ['seat', 'fare']
        

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
    class Meta:
        model = Feedback
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter your feedback'}),
        }

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
        fields = ['name', 'number_plate', 'driver', 'manager', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'number_plate': forms.TextInput(attrs={'class': 'form-control'}),
            'driver': forms.Select(attrs={'class': 'form-control'}),
            'manager': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
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