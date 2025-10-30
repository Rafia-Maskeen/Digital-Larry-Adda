from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Vehicle, Seat, Route, Booking, Feedback, Issue, VehicleLocation
from .models import AIInteraction

admin.site.register(Route)
admin.site.register(Booking)
admin.site.register(Seat)
admin.site.register(VehicleLocation)

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone_number', 'address')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('phone_number', 'address')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)

class VehicleAdmin(admin.ModelAdmin):
    list_display = ('name', 'number_plate', 'manager', 'status')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(manager=request.user)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.manager = request.user
        obj.save()

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return self.readonly_fields + ('manager',)
        return self.readonly_fields

admin.site.register(Vehicle, VehicleAdmin)

class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('user', 'route', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'route__start_location', 'route__end_location', 'comment')

class IssueAdmin(admin.ModelAdmin):
    list_display = ('user', 'route', 'booking', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'description')
    list_editable = ('status',)

admin.site.register(Feedback, FeedbackAdmin)
admin.site.register(Issue, IssueAdmin)

# 👈 NEW: Add to admin.py


@admin.register(AIInteraction)
class AIInteractionAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'created_at')
    search_fields = ('question', 'response')
    list_filter = ('created_at',)