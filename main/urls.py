from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('find-ride/', views.find_ride, name='find_ride'),
    path('add-vehicles/', views.add_update_vehicle, name='add-vehicles'),
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
    path('feedbacks/', views.feedback_list, name='feedback_list'),
    path('feedbacks/add/', views.feedback_add, name='feedback_add'),
    path('feedbacks/<int:pk>/edit/', views.feedback_edit, name='feedback_edit'),
    path('feedbacks/<int:pk>/delete/', views.feedback_delete, name='feedback_delete'),
    path('issues/', views.issue_list, name='issue_list'),
    path('issues/add/', views.issue_add, name='issue_add'),
    path('issues/<int:pk>/edit/', views.issue_edit, name='issue_edit'),
    path('issues/<int:pk>/delete/', views.issue_delete, name='issue_delete'),


    
    # Issue
    path('manager-dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('add-vehicle/', views.add_update_vehicle, name='add_vehicle'),
    path('update-vehicle/<int:pk>/', views.add_update_vehicle, name='update_vehicle'),
    path('monitor-map/', views.monitor_map, name='monitor_map'),
   path('driver/vehicle-locations/', views.driver_vehicle_location_list, name='driver_vehicle_location_list'),
    path('driver/vehicle-locations/add/', views.driver_vehicle_location_add, name='driver_vehicle_location_add'),
    path('driver/vehicle-locations/<int:loc_id>/edit/', views.driver_vehicle_location_edit, name='driver_vehicle_location_edit'),
    path('driver/vehicle-locations/<int:loc_id>/delete/', views.driver_vehicle_location_delete, name='driver_vehicle_location_delete'),
    path('vehicle-locations-json/', views.vehicle_locations_json, name='vehicle_locations_json'),
    path('assign-route/', views.assign_route, name='assign_route'),
    path('api/transport-data/', views.transport_data_api, name='transport_data_api'),
    path('chatbot/', views.chatbot_view, name='chatbot'),
    path("api/routes/", views.get_user_routes, name="get_user_routes"),
    path("api/bookings/", views.get_user_bookings, name="get_user_bookings"),
    path('ai-assistant/', views.ai_assistant, name='ai_assistant'),
    path('driver/dashboard/', views.driver_dashboard, name='driver_dashboard'),
    path('driver/seats/', views.driver_seat_list, name='driver_seat_list'),
    path('driver/seats/add/', views.driver_seat_add, name='driver_seat_add'),
    path('driver/seats/<int:seat_id>/edit/', views.driver_seat_edit, name='driver_seat_edit'),
    path('driver/seats/<int:seat_id>/delete/', views.driver_seat_delete, name='driver_seat_delete'),
    path("contact-admin/", views.contact_admin, name="contact_admin"),
    path("driver-login/", views.driver_login, name="driver_login"),
    path("manager-login/", views.manager_login, name="manager_login"),





]