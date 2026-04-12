from django.contrib import admin
from .models import EventLog


@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'event_type', 'user_id', 'product_id', 'timestamp', 'device')
    list_filter = ('event_type', 'device')
    search_fields = ('user_id', 'session_id', 'product_id')
    readonly_fields = ('event_hash', 'received_at')
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
