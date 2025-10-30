from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('find-ride/', views.find_ride, name='find_ride'),
    path('vehicles/', views.vehicles, name='vehicles'),
    path('vehicles/<int:pk>/', views.vehicle_detail, name='vehicle_detail'),
    path('available-vehicles/', views.available_vehicles, name='available_vehicles'),
    path('book-route/<int:route_id>/', views.book_route, name='book_route'),
    path('booking-success/', views.booking_success, name='booking_success'),
    path('register/', views.register_view, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('routes/', views.all_routes_with_vehicles, name='route_list'),
    path('routes/<int:route_id>/', views.route_detail, name='route_detail'),
    path('feedback/submit/', views.submit_feedback, name='submit_feedback_global'),
    path('feedback/<int:route_id>/', views.submit_feedback, name='submit_feedback'),
    
    # Issue
    path('issue/', views.submit_issue, name='submit_issue'),
    path('ai-assistant/', views.ai_assistant, name='ai_assistant'),
    path('manager-dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('add-vehicle/', views.add_update_vehicle, name='add_vehicle'),
    path('update-vehicle/<int:pk>/', views.add_update_vehicle, name='update_vehicle'),
    path('monitor-map/', views.monitor_map, name='monitor_map'),
    path('vehicle-locations/', views.vehicle_locations_json, name='vehicle_locations_json'),
    path('assign-route/', views.assign_route, name='assign_route'),
]