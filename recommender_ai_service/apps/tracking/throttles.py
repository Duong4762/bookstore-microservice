"""Custom throttle classes for the tracking app."""
from rest_framework.throttling import AnonRateThrottle


class EventCollectorThrottle(AnonRateThrottle):
    """
    60 events per minute per IP.
    Prevents frontend bugs / malicious spam from flooding event_logs.
    Rate can be overridden in settings: REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['event_collector']
    """
    scope = 'event_collector'
