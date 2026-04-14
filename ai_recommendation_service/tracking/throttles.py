from rest_framework.throttling import AnonRateThrottle


class EventCollectorThrottle(AnonRateThrottle):
    scope = 'event_collector'
