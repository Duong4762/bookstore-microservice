from django.contrib import admin

from .models import EventLog


@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_id', 'event_type', 'product_id', 'timestamp')
    list_filter = ('event_type',)
    search_fields = ('session_id', 'keyword')
